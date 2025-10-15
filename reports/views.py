from django.db.models import Q, Count, Sum, Avg, F
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime, timedelta, date
from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
import csv
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import openpyxl
from openpyxl.styles import Font, Alignment

from .models import ReportTemplate, ReportExecution, ScheduledReport, ReportFavorite
from .serializers import (
    ReportTemplateSerializer, ReportTemplateDetailSerializer,
    ReportExecutionSerializer, ReportExecutionCreateSerializer,
    ScheduledReportSerializer, ReportFavoriteSerializer,
    ReportStatsSerializer, PatientListReportSerializer,
    AppointmentReportSerializer, FinancialReportSerializer
)
from patients.models import Patient
from appointments.models import Appointment
from billing.models import Invoice, Payment
from administration.models import Provider, Facility


class ReportTemplateViewSet(viewsets.ModelViewSet):
    """Report template management"""
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['report_type', 'is_public', 'is_active']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user access
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                Q(is_public=True) | 
                Q(created_by=self.request.user) |
                Q(allowed_users=self.request.user)
            ).distinct()
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ReportTemplateDetailSerializer
        return ReportTemplateSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get popular reports"""
        popular = self.get_queryset().annotate(
            execution_count=Count('executions')
        ).order_by('-execution_count')[:10]
        
        serializer = self.get_serializer(popular, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recently used reports"""
        recent = self.get_queryset().filter(
            executions__executed_by=request.user
        ).distinct().order_by('-executions__created_at')[:10]
        
        serializer = self.get_serializer(recent, many=True)
        return Response(serializer.data)


class ReportExecutionViewSet(viewsets.ModelViewSet):
    """Report execution management"""
    queryset = ReportExecution.objects.all()
    serializer_class = ReportExecutionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['template', 'status', 'output_format']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Users can only see their own executions unless they're superuser
        if not self.request.user.is_superuser:
            queryset = queryset.filter(executed_by=self.request.user)
        
        return queryset.select_related('template', 'executed_by').order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ReportExecutionCreateSerializer
        return ReportExecutionSerializer
    
    def perform_create(self, serializer):
        execution = serializer.save(
            executed_by=self.request.user,
            started_at=timezone.now(),
            status='running'
        )
        
        # Execute the report asynchronously (you might want to use Celery for this)
        self._execute_report(execution)
    
    def _execute_report(self, execution):
        """Execute the report (simplified version)"""
        try:
            template = execution.template
            parameters = execution.parameters
            
            # Generate report data based on template type
            if template.report_type == 'patient_list':
                data = self._generate_patient_list_report(parameters)
            elif template.report_type == 'appointment_report':
                data = self._generate_appointment_report(parameters)
            elif template.report_type == 'financial_report':
                data = self._generate_financial_report(parameters)
            else:
                raise ValueError(f"Unknown report type: {template.report_type}")
            
            # Generate output file
            file_path = self._generate_output_file(execution, data)
            
            # Update execution status
            execution.status = 'completed'
            execution.completed_at = timezone.now()
            execution.execution_time = execution.completed_at - execution.started_at
            execution.result_count = len(data)
            execution.file_path = file_path
            execution.save()
            
        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.completed_at = timezone.now()
            execution.save()
    
    def _generate_patient_list_report(self, parameters):
        """Generate patient list report data"""
        queryset = Patient.objects.all()
        
        # Apply filters
        if parameters.get('start_date'):
            queryset = queryset.filter(created_at__date__gte=parameters['start_date'])
        if parameters.get('end_date'):
            queryset = queryset.filter(created_at__date__lte=parameters['end_date'])
        if parameters.get('provider_id'):
            queryset = queryset.filter(primary_care_physician_id=parameters['provider_id'])
        if parameters.get('gender'):
            queryset = queryset.filter(gender=parameters['gender'])
        if not parameters.get('include_inactive', False):
            queryset = queryset.filter(is_active=True)
        
        # Convert to list of dictionaries
        data = []
        for patient in queryset:
            data.append({
                'Patient ID': str(patient.id),
                'Name': patient.get_full_name(),
                'Date of Birth': patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else '',
                'Gender': patient.get_gender_display(),
                'Phone': patient.phone_home or patient.phone_mobile or '',
                'Email': patient.email or '',
                'Primary Care Physician': patient.primary_care_physician.full_name if patient.primary_care_physician else '',
                'Created Date': patient.created_at.strftime('%Y-%m-%d'),
                'Status': 'Active' if patient.is_active else 'Inactive'
            })
        
        return data
    
    def _generate_appointment_report(self, parameters):
        """Generate appointment report data"""
        queryset = Appointment.objects.all()
        
        # Apply filters
        if parameters.get('start_date'):
            queryset = queryset.filter(appointment_date__date__gte=parameters['start_date'])
        if parameters.get('end_date'):
            queryset = queryset.filter(appointment_date__date__lte=parameters['end_date'])
        if parameters.get('provider_id'):
            queryset = queryset.filter(provider_id=parameters['provider_id'])
        if parameters.get('status'):
            queryset = queryset.filter(status=parameters['status'])
        
        # Convert to list of dictionaries
        data = []
        for appointment in queryset.select_related('patient', 'provider', 'appointment_type'):
            data.append({
                'Appointment ID': str(appointment.id),
                'Date': appointment.appointment_date.strftime('%Y-%m-%d'),
                'Time': appointment.appointment_date.strftime('%H:%M'),
                'Patient': appointment.patient.get_full_name(),
                'Provider': appointment.provider.full_name if appointment.provider else '',
                'Type': appointment.appointment_type.name if appointment.appointment_type else '',
                'Duration': f"{appointment.duration} minutes",
                'Status': appointment.get_status_display(),
                'Chief Complaint': appointment.chief_complaint or '',
                'Notes': appointment.notes or ''
            })
        
        return data
    
    def _generate_financial_report(self, parameters):
        """Generate financial report data"""
        start_date = parameters.get('start_date')
        end_date = parameters.get('end_date')
        
        # Get invoices and payments in date range
        invoices = Invoice.objects.filter(
            invoice_date__date__gte=start_date,
            invoice_date__date__lte=end_date
        )
        
        payments = Payment.objects.filter(
            payment_date__date__gte=start_date,
            payment_date__date__lte=end_date
        )
        
        # Apply additional filters
        if parameters.get('provider_id'):
            # Filter by provider through medical records
            invoices = invoices.filter(medical_record__provider_id=parameters['provider_id'])
        
        # Generate summary data
        data = []
        
        # Invoice summary
        invoice_summary = invoices.aggregate(
            total_invoices=Count('id'),
            total_amount=Sum('total_amount'),
            total_paid=Sum('paid_amount'),
            total_balance=Sum('balance_due')
        )
        
        data.append({
            'Category': 'Invoice Summary',
            'Total Invoices': invoice_summary['total_invoices'] or 0,
            'Total Amount': f"${invoice_summary['total_amount'] or 0:,.2f}",
            'Total Paid': f"${invoice_summary['total_paid'] or 0:,.2f}",
            'Total Balance': f"${invoice_summary['total_balance'] or 0:,.2f}",
        })
        
        # Payment summary
        payment_summary = payments.aggregate(
            total_payments=Count('id'),
            total_amount=Sum('amount')
        )
        
        data.append({
            'Category': 'Payment Summary',
            'Total Payments': payment_summary['total_payments'] or 0,
            'Total Amount': f"${payment_summary['total_amount'] or 0:,.2f}",
            'Average Payment': f"${(payment_summary['total_amount'] or 0) / max(payment_summary['total_payments'] or 1, 1):,.2f}",
        })
        
        return data
    
    def _generate_output_file(self, execution, data):
        """Generate output file based on format"""
        if execution.output_format == 'csv':
            return self._generate_csv(execution, data)
        elif execution.output_format == 'excel':
            return self._generate_excel(execution, data)
        elif execution.output_format == 'pdf':
            return self._generate_pdf(execution, data)
        else:
            raise ValueError(f"Unsupported output format: {execution.output_format}")
    
    def _generate_csv(self, execution, data):
        """Generate CSV file"""
        if not data:
            return None
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        # In a real implementation, you would save this to a file
        return f"reports/{execution.id}.csv"
    
    def _generate_excel(self, execution, data):
        """Generate Excel file"""
        if not data:
            return None
        
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = execution.template.name
        
        # Add headers
        headers = list(data[0].keys())
        for col, header in enumerate(headers, 1):
            cell = worksheet.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal='center')
        
        # Add data
        for row, item in enumerate(data, 2):
            for col, header in enumerate(headers, 1):
                worksheet.cell(row=row, column=col, value=item[header])
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # In a real implementation, you would save this to a file
        return f"reports/{execution.id}.xlsx"
    
    def _generate_pdf(self, execution, data):
        """Generate PDF file"""
        if not data:
            return None
        
        # In a real implementation, you would create a proper PDF
        # This is a simplified version
        return f"reports/{execution.id}.pdf"
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download report file"""
        execution = self.get_object()
        
        if execution.status != 'completed' or not execution.file_path:
            return Response(
                {'error': 'Report not available for download'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # In a real implementation, you would serve the actual file
        return Response({
            'message': 'Download would start here',
            'file_path': execution.file_path,
            'format': execution.output_format
        })


class ReportAnalyticsViewSet(viewsets.ViewSet):
    """Report analytics and statistics"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Report system overview"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Basic statistics
        total_templates = ReportTemplate.objects.filter(is_active=True).count()
        total_executions = ReportExecution.objects.count()
        executions_today = ReportExecution.objects.filter(created_at__date=today).count()
        executions_this_week = ReportExecution.objects.filter(created_at__date__gte=week_ago).count()
        executions_this_month = ReportExecution.objects.filter(created_at__date__gte=month_ago).count()
        
        # Popular reports
        popular_reports = ReportTemplate.objects.annotate(
            execution_count=Count('executions')
        ).order_by('-execution_count')[:5]
        
        popular_reports_data = [
            {
                'id': str(report.id),
                'name': report.name,
                'type': report.report_type,
                'execution_count': report.execution_count
            }
            for report in popular_reports
        ]
        
        # Recent executions
        recent_executions = ReportExecution.objects.select_related(
            'template', 'executed_by'
        ).order_by('-created_at')[:10]
        
        recent_executions_data = [
            {
                'id': str(execution.id),
                'template_name': execution.template.name,
                'executed_by': execution.executed_by.get_full_name(),
                'status': execution.status,
                'created_at': execution.created_at
            }
            for execution in recent_executions
        ]
        
        # Execution status summary
        status_summary = ReportExecution.objects.values('status').annotate(
            count=Count('id')
        )
        
        data = {
            'total_templates': total_templates,
            'total_executions': total_executions,
            'executions_today': executions_today,
            'executions_this_week': executions_this_week,
            'executions_this_month': executions_this_month,
            'popular_reports': popular_reports_data,
            'recent_executions': recent_executions_data,
            'execution_status_summary': list(status_summary)
        }
        
        serializer = ReportStatsSerializer(data)
        return Response(serializer.data)


class BuiltInReportsViewSet(viewsets.ViewSet):
    """Built-in report generators"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def patient_list(self, request):
        """Generate patient list report"""
        serializer = PatientListReportSerializer(data=request.data)
        if serializer.is_valid():
            # Create a temporary execution for tracking
            execution = ReportExecution.objects.create(
                template_id=None,  # Built-in report
                executed_by=request.user,
                parameters=serializer.validated_data,
                output_format=request.data.get('output_format', 'json'),
                status='running',
                started_at=timezone.now()
            )
            
            try:
                data = self._generate_patient_list_report(serializer.validated_data)
                execution.status = 'completed'
                execution.completed_at = timezone.now()
                execution.result_count = len(data)
                execution.save()
                
                return Response({
                    'execution_id': execution.id,
                    'data': data,
                    'total_records': len(data)
                })
            except Exception as e:
                execution.status = 'failed'
                execution.error_message = str(e)
                execution.save()
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def appointment_report(self, request):
        """Generate appointment report"""
        serializer = AppointmentReportSerializer(data=request.data)
        if serializer.is_valid():
            data = self._generate_appointment_report(serializer.validated_data)
            return Response({
                'data': data,
                'total_records': len(data)
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def financial_report(self, request):
        """Generate financial report"""
        serializer = FinancialReportSerializer(data=request.data)
        if serializer.is_valid():
            data = self._generate_financial_report(serializer.validated_data)
            return Response({
                'data': data,
                'total_records': len(data)
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _generate_patient_list_report(self, parameters):
        """Generate patient list report data"""
        # Same as in ReportExecutionViewSet
        queryset = Patient.objects.all()
        
        # Apply filters
        if parameters.get('start_date'):
            queryset = queryset.filter(created_at__date__gte=parameters['start_date'])
        if parameters.get('end_date'):
            queryset = queryset.filter(created_at__date__lte=parameters['end_date'])
        if parameters.get('provider_id'):
            queryset = queryset.filter(primary_care_physician_id=parameters['provider_id'])
        if parameters.get('gender'):
            queryset = queryset.filter(gender=parameters['gender'])
        if not parameters.get('include_inactive', False):
            queryset = queryset.filter(is_active=True)
        
        # Convert to list of dictionaries
        data = []
        for patient in queryset.select_related('primary_care_physician__user'):
            data.append({
                'id': str(patient.id),
                'medical_record_number': patient.medical_record_number or '',
                'name': patient.get_full_name(),
                'date_of_birth': patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else '',
                'gender': patient.get_gender_display(),
                'phone': patient.phone_home or patient.phone_mobile or '',
                'email': patient.email or '',
                'address': f"{patient.address_line1 or ''} {patient.city or ''} {patient.state or ''}".strip(),
                'primary_care_physician': patient.primary_care_physician.full_name if patient.primary_care_physician else '',
                'created_date': patient.created_at.strftime('%Y-%m-%d'),
                'status': 'Active' if patient.is_active else 'Inactive'
            })
        
        return data
    
    def _generate_appointment_report(self, parameters):
        """Generate appointment report data"""
        # Same implementation as in ReportExecutionViewSet
        queryset = Appointment.objects.all()
        
        # Apply filters
        if parameters.get('start_date'):
            queryset = queryset.filter(appointment_date__date__gte=parameters['start_date'])
        if parameters.get('end_date'):
            queryset = queryset.filter(appointment_date__date__lte=parameters['end_date'])
        if parameters.get('provider_id'):
            queryset = queryset.filter(provider_id=parameters['provider_id'])
        if parameters.get('status'):
            queryset = queryset.filter(status=parameters['status'])
        
        data = []
        for appointment in queryset.select_related('patient', 'provider__user', 'appointment_type'):
            data.append({
                'id': str(appointment.id),
                'date': appointment.appointment_date.strftime('%Y-%m-%d'),
                'time': appointment.appointment_date.strftime('%H:%M'),
                'patient': appointment.patient.get_full_name(),
                'patient_phone': appointment.patient.phone_home or appointment.patient.phone_mobile or '',
                'provider': appointment.provider.full_name if appointment.provider else '',
                'type': appointment.appointment_type.name if appointment.appointment_type else '',
                'duration': appointment.duration,
                'status': appointment.get_status_display(),
                'chief_complaint': appointment.chief_complaint or '',
                'notes': appointment.notes or ''
            })
        
        return data
    
    def _generate_financial_report(self, parameters):
        """Generate financial report data"""
        # Same implementation as in ReportExecutionViewSet
        start_date = parameters.get('start_date')
        end_date = parameters.get('end_date')
        
        # Get invoices and payments in date range
        invoices = Invoice.objects.filter(
            invoice_date__date__gte=start_date,
            invoice_date__date__lte=end_date
        )
        
        payments = Payment.objects.filter(
            payment_date__date__gte=start_date,
            payment_date__date__lte=end_date
        )
        
        # Apply additional filters
        if parameters.get('provider_id'):
            invoices = invoices.filter(medical_record__provider_id=parameters['provider_id'])
        
        # Generate detailed financial data
        data = []
        
        # Daily breakdown if requested
        if parameters.get('group_by') == 'day':
            current_date = start_date
            while current_date <= end_date:
                daily_invoices = invoices.filter(invoice_date__date=current_date)
                daily_payments = payments.filter(payment_date__date=current_date)
                
                daily_summary = daily_invoices.aggregate(
                    invoice_count=Count('id'),
                    invoice_amount=Sum('total_amount')
                )
                
                payment_summary = daily_payments.aggregate(
                    payment_count=Count('id'),
                    payment_amount=Sum('amount')
                )
                
                data.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'invoices': daily_summary['invoice_count'] or 0,
                    'invoice_amount': f"${daily_summary['invoice_amount'] or 0:,.2f}",
                    'payments': payment_summary['payment_count'] or 0,
                    'payment_amount': f"${payment_summary['payment_amount'] or 0:,.2f}",
                })
                
                current_date += timedelta(days=1)
        
        return data


class ReportFavoriteViewSet(viewsets.ModelViewSet):
    """Report favorites management"""
    queryset = ReportFavorite.objects.all()
    serializer_class = ReportFavoriteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return super().get_queryset().filter(
            user=self.request.user
        ).select_related('template')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
