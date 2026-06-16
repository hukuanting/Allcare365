"""
Healthcare 365 穿戴式裝置數據模擬器
用於測試實時風險分析系統
"""

import requests
import time
import random
import json
import math
from datetime import datetime, timedelta
import threading


class WearableDataSimulator:
    """穿戴式裝置數據模擬器"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.is_running = False
        self.simulation_thread = None
        
        # 模擬的基準生命體徵
        self.baseline_vitals = {
            'heart_rate': 75,
            'systolic_bp': 120,
            'diastolic_bp': 80,
            'oxygen_saturation': 98,
            'respiration_rate': 16,
            'skin_temperature': 36.5
        }
        
        # 模擬情境
        self.scenarios = {
            'normal': {'name': '正常狀態', 'variation': 0.1},
            'stress': {'name': '壓力狀態', 'variation': 0.2},
            'exercise': {'name': '運動狀態', 'variation': 0.3},
            'emergency': {'name': '緊急狀態', 'variation': 0.5}
        }
        
        self.current_scenario = 'normal'
    
    def start_simulation(self, device_id="1638487", patient_mrn="anon_1", interval=1):
        """開始數據模擬"""
        if self.is_running:
            print("模擬器已在運行中")
            return
        
        self.is_running = True
        self.device_id = device_id
        self.patient_mrn = patient_mrn
        self.interval = interval
        
        print(f"🚀 開始模擬穿戴式裝置數據")
        print(f"   設備ID: {device_id}")
        print(f"   患者MRN: {patient_mrn}")
        print(f"   更新間隔: 5秒")
        print(f"   目標URL: {self.base_url}/api/wearable/receive-vital-signs/")
        
        self.simulation_thread = threading.Thread(target=self._simulation_loop)
        self.simulation_thread.daemon = True
        self.simulation_thread.start()
    
    def stop_simulation(self):
        """停止數據模擬"""
        self.is_running = False
        if self.simulation_thread:
            self.simulation_thread.join()
        print("🛑 數據模擬已停止")
    
    def change_scenario(self, scenario):
        """切換模擬情境"""
        if scenario in self.scenarios:
            self.current_scenario = scenario
            print(f"📊 切換到情境: {self.scenarios[scenario]['name']}")
        else:
            print(f"❌ 未知情境: {scenario}")
    
    def _simulation_loop(self):
        """模擬數據循環"""
        sequence = 0
        
        while self.is_running:
            try:
                # 生成模擬數據
                vital_data = self._generate_vital_signs(sequence)
                
                # 發送到API
                success = self._send_vital_signs(vital_data)
                
                if success:
                    print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] 數據已發送 - 心率:{vital_data['heart_rate']}, 血壓:{vital_data['systolic_bp']}/{vital_data['diastolic_bp']}, 血氧:{vital_data['oxygen_saturation']}%")
                else:
                    print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] 數據發送失敗")
                
                sequence += 1
                time.sleep(self.interval)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ 模擬錯誤: {str(e)}")
                time.sleep(self.interval)
    
    def _generate_vital_signs(self, sequence):
        """生成模擬的生命體徵數據"""
        scenario = self.scenarios[self.current_scenario]
        variation = scenario['variation']
        
        # 基於時間的週期性變化
        time_factor = sequence * 0.1
        
        # 生成帶有變異的生命體徵
        vitals = {}
        
        # 心率 (50-180 bpm)
        base_hr = self.baseline_vitals['heart_rate']
        if self.current_scenario == 'exercise':
            base_hr += 40
        elif self.current_scenario == 'emergency':
            base_hr += 60
        
        vitals['heart_rate'] = max(50, min(180, 
            base_hr + random.uniform(-base_hr * variation, base_hr * variation) + 
            5 * math.sin(time_factor)
        ))
        
        # 血壓
        base_sbp = self.baseline_vitals['systolic_bp']
        base_dbp = self.baseline_vitals['diastolic_bp']
        
        if self.current_scenario == 'stress':
            base_sbp += 20
            base_dbp += 10
        elif self.current_scenario == 'emergency':
            base_sbp += 40
            base_dbp += 20
        
        vitals['systolic_bp'] = max(80, min(200,
            base_sbp + random.uniform(-base_sbp * variation, base_sbp * variation)
        ))
        vitals['diastolic_bp'] = max(50, min(120,
            base_dbp + random.uniform(-base_dbp * variation, base_dbp * variation)
        ))
        vitals['mean_arterial_pressure'] = round(
            (vitals['systolic_bp'] + 2 * vitals['diastolic_bp']) / 3
        )
        
        # 血氧飽和度 (85-100%)
        base_spo2 = self.baseline_vitals['oxygen_saturation']
        if self.current_scenario == 'emergency':
            base_spo2 -= 8
        
        vitals['oxygen_saturation'] = max(85, min(100,
            base_spo2 + random.uniform(-base_spo2 * variation * 0.1, base_spo2 * variation * 0.1)
        ))
        
        # 呼吸頻率 (8-40 breaths/min)
        base_rr = self.baseline_vitals['respiration_rate']
        if self.current_scenario == 'exercise':
            base_rr += 8
        elif self.current_scenario == 'emergency':
            base_rr += 12
        
        vitals['respiration_rate'] = max(8, min(40,
            base_rr + random.uniform(-base_rr * variation, base_rr * variation)
        ))
        
        # 皮膚溫度
        base_temp = self.baseline_vitals['skin_temperature']
        vitals['skin_temperature'] = max(35.0, min(40.0,
            base_temp + random.uniform(-variation, variation)
        ))
        
        # 姿態 (隨機變化)
        postures = ['BACK', 'LEFT', 'RIGHT', 'SITTING']
        if sequence % 30 == 0:  # 每30秒可能改變姿態
            vitals['posture'] = random.choice(postures)
        
        # 活動強度
        if self.current_scenario == 'exercise':
            vitals['activity_level'] = random.uniform(0.7, 1.0)
        else:
            vitals['activity_level'] = random.uniform(0.0, 0.3)
        
        # 數據品質
        vitals['signal_quality'] = {
            'ecg': random.uniform(0.8, 1.0),
            'ppg': random.uniform(0.8, 1.0),
            'accelerometer': random.uniform(0.9, 1.0)
        }
        
        # 四捨五入數值
        for key in ['heart_rate', 'oxygen_saturation', 'respiration_rate', 'skin_temperature']:
            if key in vitals:
                vitals[key] = round(vitals[key], 1)
        
        # 整數值
        for key in ['systolic_bp', 'diastolic_bp', 'mean_arterial_pressure']:
            if key in vitals:
                vitals[key] = int(round(vitals[key]))
        
        return vitals
    
    def _send_vital_signs(self, vital_data):
        """發送生命體徵數據到API"""
        try:
            payload = {
                'device_id': self.device_id,
                'patient_mrn': self.patient_mrn,
                'timestamp': datetime.now().isoformat(),
                **vital_data
            }
            
            response = requests.post(
                f"{self.base_url}/api/wearable/receive-vital-signs/",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            
            return response.status_code == 200
            
        except requests.exceptions.RequestException as e:
            print(f"API請求失敗: {str(e)}")
            return False
        except Exception as e:
            print(f"發送數據錯誤: {str(e)}")
            return False


def main():
    """主函數 - 交互式數據模擬器"""
    
    simulator = WearableDataSimulator()
    
    print("🏥 Healthcare 365 穿戴式裝置數據模擬器")
    print("=" * 50)
    print("指令:")
    print("  start [device_id] [patient_mrn] - 開始模擬")
    print("    範例: start 1638487 anon_1")
    print("  stop - 停止模擬")
    print("  scenario [normal|stress|exercise|emergency] - 切換情境")
    print("  status - 顯示狀態")
    print("  quit - 退出")
    print()
    
    try:
        while True:
            command = input("模擬器> ").strip().split()
            
            if not command:
                continue
            
            if command[0] == 'start':
                device_id = command[1] if len(command) > 1 else "1638487"
                patient_mrn = command[2] if len(command) > 2 else "anon_1"
                simulator.start_simulation(device_id, patient_mrn)
                
            elif command[0] == 'stop':
                simulator.stop_simulation()
                
            elif command[0] == 'scenario':
                if len(command) > 1:
                    simulator.change_scenario(command[1])
                else:
                    print("可用情境: normal, stress, exercise, emergency")
                    
            elif command[0] == 'status':
                status = "運行中" if simulator.is_running else "已停止"
                print(f"模擬器狀態: {status}")
                if simulator.is_running:
                    print(f"當前情境: {simulator.scenarios[simulator.current_scenario]['name']}")
                    print(f"設備ID: {simulator.device_id}")
                    print(f"患者MRN: {simulator.patient_mrn}")
                    
            elif command[0] in ['quit', 'exit']:
                simulator.stop_simulation()
                print("再見!")
                break
                
            else:
                print("未知指令，請輸入 start, stop, scenario, status 或 quit")
                
    except KeyboardInterrupt:
        simulator.stop_simulation()
        print("\n模擬器已停止")


if __name__ == "__main__":
    main()