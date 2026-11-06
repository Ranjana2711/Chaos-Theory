Start-Process powershell -ArgumentList '-NoExit','-Command','cd "C:\project\Chaos Theory"; venv\Scripts\activate; python app.py'
Start-Sleep -Seconds 25
Start-Process powershell -ArgumentList '-NoExit','-Command','cloudflared tunnel --url http://localhost:7860'
