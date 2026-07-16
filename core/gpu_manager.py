import subprocess

class GPUManager:

    @staticmethod
    def get_gpu_info():
        try:
            import onnxruntime as ort
            providers = ort.get_available_providers()
            has_cuda = "CUDAExecutionProvider" in providers
        except ImportError:
            has_cuda = False

        # Try to get the GPU name via nvidia-smi
        gpu_name = "Unknown GPU"
        try:
            result = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.free", "--format=csv,noheader,nounits"],
                encoding="utf-8",
                stderr=subprocess.DEVNULL
            ).strip()
            
            if result:
                # E.g. "NVIDIA GeForce RTX 3050, 4096"
                parts = result.split(",")
                if len(parts) >= 1:
                    gpu_name = parts[0].strip()
        except Exception:
            if not has_cuda:
                gpu_name = "CUDA Not Available"

        return {
            "available": has_cuda,
            "name": gpu_name
        }