import subprocess
from dotenv import load_dotenv

load_dotenv()


if __name__ == "__main__":
    cmd = "streamlit run src/streamlit_app/main.py"
    subprocess.run(cmd, shell=True)
