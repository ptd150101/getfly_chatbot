
#!/usr/bin/env bash
eval "$(conda shell.bash hook)"
conda activate chatbot_env
cd ..
python run.py
