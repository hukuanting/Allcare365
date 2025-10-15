from django.shortcuts import render
from django.db.models import Q, Count, Sum, F, DecimalField
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    InsuranceProvider, PatientInsurance, Invoice, InvoiceLineItem,
    Payment, InsuranceClaim, BillingCode, FeeSchedule
)
from .serializers import (
    InsuranceProviderSerializer, PatientInsuranceSerializer,
    InvoiceSerializer, InvoiceDetailSerializer, InvoiceLineItemSerializer,
    PaymentSerializer, InsuranceClaimSerializer, BillingCodeSerializer,
    FeeScheduleSerializer, BillingStatisticsSerializer, PatientBillingSerializer,
    RevenueSummarySerializer, AgingReportSerializer
)
from patients.models import Patient


class InsuranceProviderViewSet(viewsets.ModelViewSet):
    """保險公司視圖集"""
    queryset = InsuranceProvider.objects.all()
    serializer_class = InsuranceProviderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """活躍的保險公司"""
        active_companies = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_companies, many=True)
        return Response(serializer.data)


class PatientInsuranceViewSet(viewsets.ModelViewSet):
    """病患保險視圖集"""
    queryset = PatientInsurance.objects.all()
    serializer_class = PatientInsuranceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'insurance_provider', 'is_active']
    
    def get_queryset(self):
        return super().get_queryset().select_related('patient', 'insurance_provider')
    
    @action(detail=False, methods=['get'])
    def by_patient(self, request):
        """按病患查詢保險"""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': '請提供病患ID'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        insurances = self.get_queryset().filter(patient_id=patient_id)
        serializer = self.get_serializer(insurances, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """活躍的病患保險"""
        active_insurances = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_insurances, many=True)
        return Response(serializer.data)


class InvoiceViewSet(viewsets.ModelViewSet):
    """發票視圖集"""
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'status']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 日期範圍篩選
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(invoice_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(invoice_date__lte=end_date)
        
        return queryset.select_related('patient', 'appointment', 'medical_record')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return InvoiceDetailSerializer
        return InvoiceSerializer
    
    def perform_create(self, serializer):
        """創建發票時自動生成發票號碼"""
        # 生成發票號碼
        today = timezone.now().date()
        invoice_count = Invoice.objects.filter(invoice_date=today).count()
        invoice_number = f"INV-{today.strftime('%Y%m%d')}-{invoice_count + 1:04d}"
        
        serializer.save(invoice_number=invoice_number)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """待付款發票"""
        pending_invoices = self.get_queryset().filter(status='pending')
        serializer = self.get_serializer(pending_invoices, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """逾期發票"""
        today = timezone.now().date()
        overdue_invoices = self.get_queryset().filter(
            status='pending',
            due_date__lt=today
        )
        serializer = self.get_serializer(overdue_invoices, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def send_invoice(self, request, pk=None):
        """發送發票"""
        invoice = self.get_object()
        
        if invoice.status != 'pending':
            return Response(
                {'error': '只有待付款的發票才能發送'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 這裡可以實現發送邏輯（電子郵件等）
        invoice.status = 'sent'
        invoice.save()
        
        return Response({'message': '發票已發送'})
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """標記為已付款"""
        invoice = self.get_object()
        
        if invoice.status == 'paid':
            return Response(
                {'error': '發票已經是已付款狀態'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invoice.status = 'paid'
        invoice.save()
        
        return Response({'message': '發票已標記為已付款'})
    
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        """添加發票項目"""
        invoice = self.get_object()
        
        if invoice.status != 'draft':
            return Response(
                {'error': '只有草稿狀態的發票才能添加項目'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = InvoiceLineItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(invoice=invoice)
            
            # 重新計算發票總額
            invoice.calculate_total()
            
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InvoiceLineItemViewSet(viewsets.ModelViewSet):
    """發票項目視圖集"""
    queryset = InvoiceLineItem.objects.all()
    serializer_class = InvoiceLineItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['invoice']
    
    def get_queryset(self):
        return super().get_queryset().select_related('invoice')
    
    def perform_update(self, serializer):
        """更新項目時重新計算發票總額"""
        item = serializer.save()
        item.invoice.calculate_total()
    
    def perform_destroy(self, instance):
        """刪除項目時重新計算發票總額"""
        invoice = instance.invoice
        super().perform_destroy(instance)
        invoice.calculate_total()


class PaymentViewSet(viewsets.ModelViewSet):
    """付款視圖集"""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['invoice', 'payment_method']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 日期範圍篩選
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(payment_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(payment_date__lte=end_date)
        
        return queryset.select_related('invoice', 'invoice__patient')
    
    def perform_create(self, serializer):
        """創建付款時更新發票狀態"""
        payment = serializer.save()
        
        # 計算發票餘額
        invoice = payment.invoice
        total_paid = invoice.payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        if total_paid >= invoice.total_amount:
            invoice.status = 'paid'
            invoice.save()
    
    @action(detail=False, methods=['get'])
    def daily_summary(self, request):
        """每日付款摘要"""
        today = timezone.now().date()
        payments = self.get_queryset().filter(payment_date__date=today)
        
        summary = payments.aggregate(
            total_amount=Sum('amount'),
            count=Count('id')
        )
        
        by_method = payments.values('payment_method').annotate(
            amount=Sum('amount'),
            count=Count('id')
        )
        
        return Response({
            'date': today,
            'total_amount': summary['total_amount'] or Decimal('0'),
            'total_count': summary['count'] or 0,
            'by_method': by_method
        })


class InsuranceClaimViewSet(viewsets.ModelViewSet):
    """保險理賠視圖集"""
    queryset = InsuranceClaim.objects.all()
    serializer_class = InsuranceClaimSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'insurance_provider', 'status']
    
    def get_queryset(self):
        return super().get_queryset().select_related('patient', 'insurance_provider')
    
    def perform_create(self, serializer):
        """創建理賠時自動生成理賠號碼"""
        today = timezone.now().date()
        claim_count = InsuranceClaim.objects.filter(claim_date__date=today).count()
        claim_number = f"CLM-{today.strftime('%Y%m%d')}-{claim_count + 1:04d}"
        
        serializer.save(claim_number=claim_number)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """待處理理賠"""
        pending_claims = self.get_queryset().filter(status='submitted')
        serializer = self.get_serializer(pending_claims, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """批准理賠"""
        claim = self.get_object()
        
        if claim.status != 'submitted':
            return Response(
                {'error': '只有已提交的理賠才能批准'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        approved_amount = request.data.get('approved_amount')
        if not approved_amount:
            return Response(
                {'error': '請提供批准金額'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        claim.status = 'approved'
        claim.approved_amount = Decimal(approved_amount)
        claim.processed_date = timezone.now()
        claim.save()
        
        return Response({'message': '理賠已批准'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """拒絕理賠"""
        claim = self.get_object()
        
        if claim.status != 'submitted':
            return Response(
                {'error': '只有已提交的理賠才能拒絕'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        claim.status = 'rejected'
        claim.rejection_reason = request.data.get('reason', '')
        claim.processed_date = timezone.now()
        claim.save()
        
        return Response({'message': '理賠已拒絕'})


class BillingCodeViewSet(viewsets.ModelViewSet):
    """計費代碼視圖集"""
    queryset = BillingCode.objects.all()
    serializer_class = BillingCodeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['code_type', 'is_active']
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """活躍的計費代碼"""
        active_codes = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_codes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """按類型查詢代碼"""
        code_type = request.query_params.get('type')
        if not code_type:
            return Response(
                {'error': '請提供代碼類型'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        codes = self.get_queryset().filter(code_type=code_type)
        serializer = self.get_serializer(codes, many=True)
        return Response(serializer.data)


class FeeScheduleViewSet(viewsets.ModelViewSet):
    """費用表視圖集"""
    queryset = FeeSchedule.objects.all()
    serializer_class = FeeScheduleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['billing_code', 'is_active']
    
    def get_queryset(self):
        return super().get_queryset().select_related('billing_code')
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """目前有效的費用表"""
        today = timezone.now().date()
        current_fees = self.get_queryset().filter(
            is_active=True,
            effective_date__lte=today
        ).filter(
            Q(expiration_date__gte=today) | Q(expiration_date__isnull=True)
        )
        
        serializer = self.get_serializer(current_fees, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_code(self, request):
        """按計費代碼查詢費用"""
        code = request.query_params.get('code')
        if not code:
            return Response(
                {'error': '請提供計費代碼'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        fees = self.get_queryset().filter(billing_code__code=code)
        serializer = self.get_serializer(fees, many=True)
        return Response(serializer.data)


class BillingStatisticsViewSet(viewsets.ViewSet):
    """計費統計視圖集"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """計費總覽"""
        # 基本統計
        total_invoices = Invoice.objects.count()
        total_revenue = Invoice.objects.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0')
        
        total_payments = Payment.objects.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        outstanding_balance = total_revenue - total_payments
        
        # 按狀態統計發票
        invoices_by_status = Invoice.objects.values('status').annotate(
            count=Count('id'),
            amount=Sum('total_amount')
        )
        
        # 按付款方式統計
        payments_by_method = Payment.objects.values('payment_method').annotate(
            count=Count('id'),
            amount=Sum('amount')
        )
        
        # 月度收入統計
        end_date = timezone.now().date()
        monthly_revenue = []
        
        for i in range(12):
            current_date = end_date.replace(day=1) - timedelta(days=i*30)
            revenue = Invoice.objects.filter(
                invoice_date__year=current_date.year,
                invoice_date__month=current_date.month
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
            
            monthly_revenue.append({
                'month': current_date.strftime('%Y-%m'),
                'revenue': revenue
            })
        
        # 熱門計費代碼
        top_billing_codes = InvoiceLineItem.objects.values('description').annotate(
            count=Count('id'),
            total_amount=Sum(F('quantity') * F('unit_price'))
        ).order_by('-total_amount')[:10]
        
        # 保險理賠摘要
        insurance_claims_summary = InsuranceClaim.objects.values('status').annotate(
            count=Count('id'),
            total_amount=Sum('claim_amount')
        )
        
        # 帳齡報告
        today = timezone.now().date()
        aging_categories = [
            ('0-30', 0, 30),
            ('31-60', 31, 60),
            ('61-90', 61, 90),
            ('90+', 91, 999)
        ]
        
        aging_report = []
        for category, min_days, max_days in aging_categories:
            start_date = today - timedelta(days=max_days)
            end_date = today - timedelta(days=min_days)
            
            invoices = Invoice.objects.filter(
                status='pending',
                due_date__gte=start_date,
                due_date__lte=end_date
            )
            
            aging_report.append({
                'category': category,
                'count': invoices.count(),
                'amount': invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
            })
        
        data = {
            'total_invoices': total_invoices,
            'total_revenue': total_revenue,
            'total_payments': total_payments,
            'outstanding_balance': outstanding_balance,
            'invoices_by_status': invoices_by_status,
            'payments_by_method': payments_by_method,
            'monthly_revenue': monthly_revenue,
            'top_billing_codes': top_billing_codes,
            'insurance_claims_summary': insurance_claims_summary,
            'aging_report': aging_report
        }
        
        serializer = BillingStatisticsSerializer(data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def patient_billing(self, request):
        """病患計費摘要"""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': '請提供病患ID'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response(
                {'error': '病患不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 病患基本資訊
        patient_info = {
            'id': patient.id,
            'name': patient.get_full_name(),
            'phone': patient.phone,
            'email': patient.email
        }
        
        # 計費統計
        invoices = Invoice.objects.filter(patient=patient)
        payments = Payment.objects.filter(invoice__patient=patient)
        
        total_invoices = invoices.count()
        total_billed = invoices.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        total_paid = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        outstanding_balance = total_billed - total_paid
        
        # 最近發票
        recent_invoices = invoices.order_by('-invoice_date')[:5]
        recent_invoices_data = InvoiceSerializer(recent_invoices, many=True).data
        
        # 最近付款
        recent_payments = payments.order_by('-payment_date')[:5]
        recent_payments_data = PaymentSerializer(recent_payments, many=True).data
        
        # 保險資訊
        insurance_info = PatientInsurance.objects.filter(patient=patient, is_active=True)
        insurance_data = PatientInsuranceSerializer(insurance_info, many=True).data
        
        # 未付款發票
        outstanding_invoices = invoices.filter(status='pending')
        outstanding_invoices_data = InvoiceSerializer(outstanding_invoices, many=True).data
        
        data = {
            'patient_info': patient_info,
            'total_invoices': total_invoices,
            'total_billed': total_billed,
            'total_paid': total_paid,
            'outstanding_balance': outstanding_balance,
            'recent_invoices': recent_invoices_data,
            'recent_payments': recent_payments_data,
            'insurance_info': insurance_data,
            'outstanding_invoices': outstanding_invoices_data
        }
        
        serializer = PatientBillingSerializer(data)
        return Response(serializer.data)
