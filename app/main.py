from fastapi import FastAPI, Form
from fastapi.responses import StreamingResponse
from app.ts_generator import generate_ts_from_abap
from app.docx_writer import create_docx
import io

app = FastAPI()

@app.post("/generate-ts/")
async def generate_ts(abap_code: str = Form(...)):
    ts_text = generate_ts_from_abap(abap_code)
    docx_buffer = io.BytesIO()
    create_docx(ts_text, docx_buffer)
    docx_buffer.seek(0)
    return StreamingResponse(
        docx_buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=technical_spec.docx"}
    )