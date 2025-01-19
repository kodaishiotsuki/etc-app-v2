"use client";

import { useState } from "react";

export default function FileUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [markdownText, setMarkdownText] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] || null);
    setErrorMessage(null);
    setMarkdownText(null);
  };

  const handleSubmit = async (
    e: React.FormEvent,
    format: "markdown" | "excel" = "markdown"
  ) => {
    e.preventDefault();
    if (!file) {
      setErrorMessage("ファイルを選択してください。");
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("format", format);

    try {
      console.log("Submitting form with format:", format);
      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      console.log("Response status:", response.status);
      const contentType = response.headers.get("content-type");
      console.log("Response content type:", contentType);

      if (!response.ok) {
        let errorMessage = "ファイル処理中にエラーが発生しました。";
        try {
          if (contentType?.includes("application/json")) {
            const errorData = await response.json();
            errorMessage = errorData.error || errorMessage;
          } else {
            const errorText = await response.text();
            errorMessage = errorText || errorMessage;
          }
        } catch (parseError) {
          console.error("Error parsing error response:", parseError);
        }
        throw new Error(errorMessage);
      }

      if (format === "excel") {
        if (!contentType?.includes("spreadsheetml")) {
          throw new Error("Excelファイルの生成に失敗しました。");
        }
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "etc_data.xlsx";
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
      } else {
        const data = await response.json();
        setMarkdownText(data.markdown);
      }
      setErrorMessage(null);
    } catch (error) {
      console.error("Error:", error);
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "予期せぬエラーが発生しました。"
      );
      setMarkdownText(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center p-6">
      <h1 className="text-2xl font-bold mb-4">PDFをアップロードして解析</h1>
      <form className="w-full max-w-md space-y-4">
        <input
          type="file"
          accept="application/pdf"
          onChange={handleFileChange}
          className="w-full p-2 border rounded-lg"
        />
        <div className="flex gap-2">
          <button
            onClick={(e) => handleSubmit(e, "markdown")}
            className="flex-1 p-2 bg-blue-500 text-white font-semibold rounded-lg hover:bg-blue-600 transition duration-200"
            disabled={loading}
          >
            {loading ? "処理中..." : "Markdownで表示"}
          </button>
          <button
            onClick={(e) => handleSubmit(e, "excel")}
            className="flex-1 p-2 bg-green-500 text-white font-semibold rounded-lg hover:bg-green-600 transition duration-200"
            disabled={loading}
          >
            {loading ? "処理中..." : "Excelでダウンロード"}
          </button>
        </div>
      </form>
      {errorMessage && (
        <div className="mt-4 text-red-500 font-semibold">{errorMessage}</div>
      )}
      {markdownText && (
        <div className="mt-4 p-4 border rounded-lg w-full">
          <h2 className="text-lg font-semibold">Markdown 内容:</h2>
          <pre className="whitespace-pre-wrap text-sm">{markdownText}</pre>
        </div>
      )}
    </div>
  );
}
