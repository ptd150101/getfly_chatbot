
#!/usr/bin/env bash
eval "$(conda shell.bash hook)"
conda activate /opt/conda/envs/chatbot_env

/opt/conda/envs/chatbot_env/bin/python /home/app/run.py
