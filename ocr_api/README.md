# OCR API Microservice

Microservicio FastAPI independiente para procesamiento OCR de tickets de compra.

## Arquitectura

- **Puerto**: 8551
- **Stack**: FastAPI + Uvicorn + Tesseract + Ollama
- **Independiente**: No modifica el código de la app principal Flet

## Características

- Extracción de texto con Tesseract OCR (español)
- Parseo inteligente con Ollama/Gemma2
- Preprocesamiento de imágenes (contraste, nitidez)
- API REST async con validación Pydantic
- Health checks integrados

## Endpoints

### GET /health
Health check del servicio.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### POST /upload-ocr
Procesa una imagen de ticket y extrae datos estructurados.

**Request:**
- `file`: Archivo de imagen (multipart/form-data)
- `familia_id`: ID de la familia (form field)

**Response:**
```json
{
  "success": true,
  "monto": 1250.0,
  "fecha": "2026-02-28",
  "comercio": "Tienda Inglesa",
  "items": ["leche", "pan", "aceite"],
  "texto_crudo": "texto extraído por tesseract...",
  "confianza_ocr": 0.85,
  "error": null
}
```

## Desarrollo Local

### Requisitos
- Python 3.12+
- Tesseract OCR instalado
- Ollama corriendo con modelo gemma2:2b

### Instalación
```bash
cd ocr_api
uv pip install -r pyproject.toml
```

### Ejecutar
```bash
python -m ocr_api.main
```

## Docker

### Build
```bash
docker-compose build ocr_api
```

### Run
```bash
docker-compose up -d ocr_api
```

### Logs
```bash
docker-compose logs -f ocr_api
```

### Status
```bash
docker-compose ps ocr_api
```

## Testing

### Health Check
```bash
curl http://localhost:8551/health
```

### Upload Test (PowerShell)
```powershell
$form = @{
    file = Get-Item -Path "ticket.jpg"
    familia_id = "1"
}
Invoke-RestMethod -Uri "http://localhost:8551/upload-ocr" -Method Post -Form $form
```

### Upload Test (Python)
```bash
python test_ocr_api.py
```

## Variables de Entorno

```env
API_HOST=0.0.0.0
API_PORT=8551
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma2:2b
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=auditor_familiar
POSTGRES_USER=auditor_user
POSTGRES_PASSWORD=tu_password
```

## Integración con App Principal

La app Flet puede llamar al microservicio vía HTTP:

```python
import httpx

async def procesar_ticket(imagen_path: str, familia_id: int):
    async with httpx.AsyncClient() as client:
        with open(imagen_path, "rb") as f:
            files = {"file": f}
            data = {"familia_id": str(familia_id)}
            response = await client.post(
                "http://localhost:8551/upload-ocr",
                files=files,
                data=data,
            )
        return response.json()
```

## Troubleshooting

### Container restarting
```bash
docker-compose logs ocr_api
```

### Tesseract not found
Verificar que tesseract-ocr esté instalado en el Dockerfile.

### Ollama connection error
Verificar que `OLLAMA_BASE_URL` apunte correctamente:
- Local: `http://localhost:11434`
- Docker: `http://host.docker.internal:11434`

## Próximos Pasos

1. ✅ Servicio funcionando
2. ✅ OCR + Parseo implementado
3. 🔄 Integrar con app Flet principal
4. 🔄 Agregar sugerencia de categoría (cosine search)
5. 🔄 Tests automatizados
