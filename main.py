from io import StringIO
from typing import Optional
from urllib.parse import quote

import pandas as pd
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


app = FastAPI(title="CSV Viewer")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.state.dataframe: Optional[pd.DataFrame] = None


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, message: Optional[str] = None) -> HTMLResponse:
    """Render the upload form and optionally show a status message."""
    return templates.TemplateResponse(
        "index.html", {"request": request, "message": message}
    )


@app.post("/upload", response_class=HTMLResponse)
async def upload_csv(file: UploadFile = File(...)) -> RedirectResponse:
    """Receive a CSV upload, parse it into a DataFrame, and store it for display."""
    contents = await file.read()
    message: str

    if file.content_type not in {"text/csv", "application/vnd.ms-excel", "application/csv"}:
        message = "Please upload a valid CSV file."
    elif not contents:
        message = "The uploaded file was empty."
    else:
        decoded: Optional[str] = None
        for encoding in ("utf-8", "latin-1"):
            try:
                decoded = contents.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if decoded is None:
            message = "Unable to decode the uploaded file. Please use UTF-8 or Latin-1 encoding."
        else:
            try:
                app.state.dataframe = pd.read_csv(StringIO(decoded))
            except Exception as exc:  # pylint: disable=broad-except
                app.state.dataframe = None
                message = f"Failed to read the CSV file: {exc}"
            else:
                row_count = len(app.state.dataframe.index)
                message = (
                    f"Successfully uploaded '{file.filename}'. Detected {row_count} rows."
                )

    url = app.url_path_for("index") + f"?message={quote(message)}"
    return RedirectResponse(url=url, status_code=303)


@app.get("/display", response_class=HTMLResponse)
async def display_data(request: Request) -> HTMLResponse:
    """Render the stored DataFrame as an HTML table if available."""
    dataframe = app.state.dataframe
    if dataframe is None:
        return templates.TemplateResponse(
            "display.html",
            {
                "request": request,
                "table": None,
                "message": "No CSV file has been uploaded yet. Please upload a file first.",
            },
        )

    table_html = dataframe.to_html(classes="data-table", index=False, border=0)
    return templates.TemplateResponse(
        "display.html",
        {"request": request, "table": table_html, "message": None},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
