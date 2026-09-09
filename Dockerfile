FROM python:3.12.7-slim@sha256:c24c34b502635f1f7c4e99dc09a2cbd85d480b7dcfd077198c6b5af138906390
WORKDIR /task
COPY spec.md task.md verify.py ./
COPY solution/ ./solution/
COPY tests/ ./tests/
ENTRYPOINT ["sh","-c","if [ \"$1\" = mutations ]; then python tests/test_verifier.py; else python verify.py; fi","--"]
