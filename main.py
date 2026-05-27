import psutil
import json
import os
import platform
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def bytes2human(n):
    symbols = ('B', 'KB', 'MB', 'GB', 'TB')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i * 10)
    for s in reversed(symbols):
        if abs(n) >= prefix[s]:
            value = float(n) / prefix[s]
            return f"{value:.2f} {s}"
    return f"{n} B"


def read_proc_file(path):
    try:
        with open(path, 'r') as f:
            return f.read().strip()
    except (PermissionError, FileNotFoundError, OSError):
        return None


IS_LINUX = platform.system() == "Linux"


# ─────────────────────────────────────────────────────────────────────────────
# 01. ИНФОРМАЦИЯ О ТЕКУЩЕМ ПРОЦЕССЕ
# ─────────────────────────────────────────────────────────────────────────────

def get_process_info():
    p = psutil.Process()
    pid = p.pid

    with p.oneshot():
        mem = p.memory_info()

        try:
            if IS_LINUX:
                fds = os.listdir(f"/proc/{pid}/fd")
                num_fds = len(fds)
                open_files = [
                    os.readlink(f"/proc/{pid}/fd/{fd}")
                    for fd in fds
                    if os.path.exists(f"/proc/{pid}/fd/{fd}")
                ]
            else:
                num_fds = p.num_fds()
                open_files = [f.path for f in p.open_files()]
        except (PermissionError, OSError):
            num_fds = None
            open_files = []

        try:
            exe_path = p.exe()
        except (psutil.AccessDenied, OSError):
            exe_path = read_proc_file(f"/proc/{pid}/exe") or "N/A"

        proc_status_raw = read_proc_file(f"/proc/{pid}/status") if IS_LINUX else None
        proc_status = {}
        if proc_status_raw:
            for line in proc_status_raw.splitlines():
                if ':' in line:
                    key, _, val = line.partition(':')
                    proc_status[key.strip()] = val.strip()

        return {
            "pid": pid,
            "name": p.name(),
            "exe_path": exe_path,
            "status": p.status(),
            "create_time": datetime.fromtimestamp(p.create_time()).isoformat(),
            "cpu_percent": p.cpu_percent(interval=0.1),
            "num_threads": p.num_threads(),
            "memory": {
                "rss":       mem.rss,
                "rss_human": bytes2human(mem.rss),
                "vms":       mem.vms,
                "vms_human": bytes2human(mem.vms),
                "percent":   round(p.memory_percent(), 3),
            },
            "file_descriptors": {
                "count":      num_fds,
                "open_files": open_files[:20],
            },
            "proc_status_extra": {
                "voluntary_ctxt_switches":    proc_status.get("voluntary_ctxt_switches"),
                "nonvoluntary_ctxt_switches": proc_status.get("nonvoluntary_ctxt_switches"),
                "vm_peak":                    proc_status.get("VmPeak"),
                "vm_rss":                     proc_status.get("VmRSS"),
            } if IS_LINUX else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 02. ИНФОРМАЦИЯ О СИСТЕМЕ
# ─────────────────────────────────────────────────────────────────────────────

def get_cpu_info():
    per_cpu = psutil.cpu_percent(interval=1, percpu=True)
    total = round(sum(per_cpu) / len(per_cpu), 2)
    freq = psutil.cpu_freq()

    cpu_model = None
    if IS_LINUX:
        cpuinfo = read_proc_file("/proc/cpuinfo")
        if cpuinfo:
            for line in cpuinfo.splitlines():
                if line.startswith("model name"):
                    cpu_model = line.split(":", 1)[1].strip()
                    break



    return {
        "model":                cpu_model or platform.processor() or "N/A",
        "logical_cpus":         psutil.cpu_count(logical=True),
        "physical_cpus":        psutil.cpu_count(logical=False),
        "total_usage_percent":  total,
        "per_cpu_usage_percent": per_cpu,
        "frequency_mhz": {
            "current": round(freq.current, 1) if freq else None,
            "min":     round(freq.min, 1)     if freq else None,
            "max":     round(freq.max, 1)     if freq else None,
        },
    }


def get_memory_info():
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()

    meminfo_extra = {}
    if IS_LINUX:
        raw = read_proc_file("/proc/meminfo")
        if raw:
            for line in raw.splitlines():
                if ':' in line:
                    key, _, val = line.partition(':')
                    meminfo_extra[key.strip()] = val.strip()

    return {
        "virtual": {
            "total":         vm.total,
            "total_human":   bytes2human(vm.total),
            "available":     vm.available,
            "avail_human":   bytes2human(vm.available),
            "used":          vm.used,
            "used_human":    bytes2human(vm.used),
            "free":          vm.free,
            "free_human":    bytes2human(vm.free),
            "percent":       vm.percent,
            "cached_human":  bytes2human(vm.cached)  if hasattr(vm, "cached")  else None,
            "buffers_human": bytes2human(vm.buffers) if hasattr(vm, "buffers") else None,
        },
        "swap": {
            "total":       sw.total,
            "total_human": bytes2human(sw.total),
            "used":        sw.used,
            "used_human":  bytes2human(sw.used),
            "free":        sw.free,
            "free_human":  bytes2human(sw.free),
            "percent":     sw.percent,
        },
        "meminfo_extra": {
            k: meminfo_extra[k]
            for k in ("MemTotal", "MemFree", "MemAvailable", "Dirty", "Writeback", "HugePages_Total")
            if k in meminfo_extra
        } if IS_LINUX else None,
    }


def get_disk_info():
    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device":      part.device,
                "mountpoint":  part.mountpoint,
                "fstype":      part.fstype,
                "total":       usage.total,
                "total_human": bytes2human(usage.total),
                "used":        usage.used,
                "used_human":  bytes2human(usage.used),
                "free":        usage.free,
                "free_human":  bytes2human(usage.free),
                "percent":     usage.percent,
            })
        except (PermissionError, OSError):
            disks.append({
                "device":     part.device,
                "mountpoint": part.mountpoint,
                "error":      "Permission denied",
            })
    return disks


def get_system_info():
    return {
        "os": {
            "system":   platform.system(),
            "release":  platform.release(),
            "version":  platform.version(),
            "hostname": platform.node(),
            "kernel":   read_proc_file("/proc/version") if IS_LINUX else None,
        },
        "cpu":    get_cpu_info(),
        "memory": get_memory_info(),
        "disks":  get_disk_info(),
    }

def main():
    data = {
        "timestamp":    datetime.now().isoformat(),
        "process_info": get_process_info(),
        "system_info":  get_system_info(),
    }

    output = json.dumps(data, indent=4, ensure_ascii=False)

    print(output)

    filename = "system_stats.json"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(output)


if __name__ == "__main__":
    main()
