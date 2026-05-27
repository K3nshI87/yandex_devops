import psutil

p = psutil.Process()

# Информация о процессе

with p.oneshot():
    name = p.name()
    memory = p.memory_info()
    exe_path = p.exe()
    
    print(f"Имя процесса: {name}")
    print(f"Потребление памяти: {memory}")
    print(f"Путь до процесса: {exe_path}")

print(f"Процесс: {p}")