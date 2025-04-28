# backend/tests/conftest.py

import os
from dotenv import load_dotenv

# 프로젝트 루트 기준으로 backend/.env 파일 읽기
dotenv_path = os.path.join(os.path.dirname(__file__), '../../backend/.env')
load_dotenv(dotenv_path)
