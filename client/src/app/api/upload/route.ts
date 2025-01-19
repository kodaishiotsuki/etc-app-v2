import { NextRequest, NextResponse } from "next/server";
import { log } from "@/lib/logger";

export async function POST(req: NextRequest) {
  const formData = await req.formData();
  const file = formData.get("file") as File | null;
  const format = (formData.get("format") as string) || "markdown";

  if (!file) {
    return NextResponse.json(
      { error: "ファイルが選択されていません。" },
      { status: 400 }
    );
  }

  try {
    const djangoApiUrl = `${process.env.NEXT_PUBLIC_DJANGO_API_URL}/upload/`;
    const backendFormData = new FormData();
    backendFormData.append("file", file);
    backendFormData.append("format", format);

    log.debug("Sending request to:", djangoApiUrl);
    log.debug("Format:", format);

    const response = await fetch(djangoApiUrl, {
      method: "POST",
      body: backendFormData,
      headers: {
        Accept:
          format === "excel"
            ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/json"
            : "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
    });

    log.debug("Response status:", response.status);
    log.debug(
      "Response headers:",
      Object.fromEntries(response.headers.entries())
    );
    log.debug("Response content type:", response.headers.get("content-type"));

    if (!response.ok) {
      let errorMessage = "バックエンド処理中にエラーが発生しました。";
      try {
        const contentType = response.headers.get("content-type");
        log.debug("Error response content type:", contentType);
        const responseText = await response.text();
        log.debug("Error response text:", responseText);

        if (contentType?.includes("application/json")) {
          try {
            const errorData = JSON.parse(responseText);
            errorMessage = errorData.error || errorData.detail || errorMessage;
          } catch (jsonError) {
            log.error("Error parsing JSON response:", jsonError);
            errorMessage = responseText || errorMessage;
          }
        } else {
          errorMessage = responseText || errorMessage;
        }
      } catch (parseError) {
        log.error("Error reading response:", parseError);
      }
      throw new Error(errorMessage);
    }

    if (format === "excel") {
      const contentType = response.headers.get("content-type");
      log.debug("Excel response content type:", contentType);

      const blob = await response.blob();
      const contentDisposition = response.headers.get("content-disposition");
      const filename = contentDisposition
        ? contentDisposition.split("filename=")[1].replace(/"/g, "")
        : "etc_data.xlsx";

      return new Response(blob, {
        headers: {
          "Content-Type":
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          "Content-Disposition": `attachment; filename=${filename}`,
        },
      });
    } else {
      const data = await response.json();
      return NextResponse.json(data);
    }
  } catch (error) {
    log.error("エラーハンドリング:", error);
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "サーバーエラーが発生しました。",
      },
      { status: 500 }
    );
  }
}
