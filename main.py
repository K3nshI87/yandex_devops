import psutil
import json
from psutil._common import bytes2human
from datetime import datetime

def convert_ntuple_to_dict(nt):
    """Конвертирует namedtuple в словарь с человеко-читаемыми значениями"""
    result = {}
    for name in nt._fields:
        value = getattr(nt, name)
        if name != 'percent':
            result[name] = value
            result[f"{name}_human"] = bytes2human(value)
        else:
            result[name] = value
    return result

def main():
    # Собираем данные
    data = {
        "timestamp": datetime.now().isoformat(),
        "process_info": {},
        "system_info": {}
    }
    
    p = psutil.Process()
    
    # Информация о процессе
    with p.oneshot():
        data["process_info"] = {
            "pid": p.pid,
            "name": p.name(),
            "exe_path": p.exe(),
            "memory_info": convert_ntuple_to_dict(p.memory_info()),
            "cpu_percent": p.cpu_percent(interval=0.1),
            "status": p.status(),
            "create_time": datetime.fromtimestamp(p.create_time()).isoformat()
        }
    
    # Информация о системе
    data["system_info"] = {
        "cpu": {
            "logical_cpus": psutil.cpu_count(),
            "physical_cpus": psutil.cpu_count(logical=False),
            "total_usage_percent": psutil.cpu_percent(interval=1),
            "per_cpu_usage_percent": psutil.cpu_percent(interval=1, percpu=True),
            "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
        },
        "memory": {
            "virtual": convert_ntuple_to_dict(psutil.virtual_memory()),
            "swap": convert_ntuple_to_dict(psutil.swap_memory())
        }
    }
    
    # Выводим JSON в консоль
    print(json.dumps(data, indent=4, ensure_ascii=False))
    
    # Сохраняем в файл
    with open('system_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

if __name__ == '__main__':
    main()