
nvidia-smi --query-gpu=timestamp,name,utilization.gpu,utilization.memory,memory.used,memory.total --format=csv,nounits -l 1 -f ${1:-gpu_usage_log.csv}
