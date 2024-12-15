import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const formData = await req.formData();
  const file = formData.get("file") as File | null;

  if (!file) {
    return NextResponse.json(
      { error: "ファイルが選択されていません。" },
      { status: 400 }
    );
  }

  try {
    const flaskApiUrl = "http://backend:4000/api/upload";
    const backendFormData = new FormData();
    backendFormData.append("file", file);

    const response = await fetch(flaskApiUrl, {
      method: "POST",
      body: backendFormData,
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.error || "バックエンド処理中にエラーが発生しました。"
      );
    }

    const data = await response.json();
    return NextResponse.json(data); // フロントにMarkdownを返す
  } catch (error) {
    console.error("エラーハンドリング:", error);
    return NextResponse.json(
      { error: "サーバーエラーが発生しました。" },
      { status: 500 }
    );
  }
}
