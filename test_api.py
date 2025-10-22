import requests

try:
    # 测试版本信息
    r = requests.get('http://localhost:8002/api/version_info', timeout=5)
    print('版本信息API:', r.status_code)
    if r.status_code == 200:
        data = r.json()
        print('最新版本:', data.get('latest_version'))
        print('文件名:', data.get('filename'))
    
    # 测试v1.0.4检查更新
    r2 = requests.get('http://localhost:8002/api/check_update?current_version=1.0.4', timeout=5)
    print()
    print('v1.0.4检查更新:', r2.status_code)
    if r2.status_code == 200:
        data2 = r2.json()
        print('有更新:', data2.get('has_update'))
        print('最新版本:', data2.get('latest_version'))
        
except Exception as e:
    print('API测试失败:', e)
