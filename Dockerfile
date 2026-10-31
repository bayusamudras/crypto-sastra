FROM python:3.12-slim
WORKDIR /app
COPY server.py scan.py hunter.py build.py unlocks.json macro.json hunt_seed.json ./
COPY site ./site
COPY static ./static
RUN python3 build.py
ENV PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python3 -c "import urllib.request,os;urllib.request.urlopen('http://localhost:'+os.environ.get('PORT','8000')+'/health')"
CMD ["python3", "server.py"]
