### Stable Diffusion LoRA utils
This is just a bunch of convenience scripts I've thrown together.

Note: some things require that https://github.com/kohya-ss/sd-scripts is
installed and configured. 

The specific components are:
 - `dataset_editor`: a web interface for convenient dataset manipulation.
   Initially based on https://github.com/gpt2ent/sd-dataset-editor/, but has
   gone through a lot of refactoring and enhancement.
 - `train_lora.py`: A helper to launch LoRA training though kohya's scripts.
   Note that the configs must be created manually. This project includes sample
   configs for your convenience.
