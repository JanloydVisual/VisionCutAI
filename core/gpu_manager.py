import torch


class GPUManager:

    @staticmethod
    def get_gpu_info():

        if torch.cuda.is_available():

            return {
                "available": True,
                "name": torch.cuda.get_device_name(0),
                "cuda": torch.version.cuda,
                "count": torch.cuda.device_count()
            }

        return {
            "available": False
        }