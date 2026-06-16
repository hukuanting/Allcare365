"""
Healthcare 365 穿戴式裝置整合 URL 配置
"""

from django.urls import path
from . import views

app_name = 'wearable_integration'

urlpatterns = [
    # 數據接收端點
    path('receive-vital-signs/', views.receive_vital_signs, name='receive_vital_signs'),
    
    # 實時數據查詢
    path('real-time-data/<str:patient_mrn>/', views.get_real_time_data, name='get_real_time_data'),
    
    # 統一風險分析端點
    path('unified-risk-analysis/<str:patient_mrn>/', views.get_unified_risk_analysis, name='get_unified_risk_analysis'),
    
    # 患者數據摘要
    path('patient-data-summary/<str:patient_mrn>/', views.get_patient_data_summary, name='get_patient_data_summary'),
]