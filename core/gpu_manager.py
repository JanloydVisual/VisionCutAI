try:
    import torch
except ImportError:
    torch = None


class GPUManager:

    @staticmethod
    def get_gpu_info():

        if torch is None:
            return {
                "available": False,
                "name": "PyTorch Not Installed"
            }

        if torch.cuda.is_available():
            return {
                "available": True,
                "name": torch.cuda.get_device_name(0)
            }

        return {
            "available": False,
            "name": "CUDA Not Available"
        }