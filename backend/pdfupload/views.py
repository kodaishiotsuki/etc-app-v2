from django.shortcuts import render
import tempfile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
import pymupdf4llm
import os


class UploadPDFView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get("file")

        if not file_obj:
            return Response(
                {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
            )

        markdown_text = ""
        issues = []

        # 一時ファイルとして保存して処理
        with tempfile.NamedTemporaryFile(delete=True) as temp_pdf:
            for chunk in file_obj.chunks():
                temp_pdf.write(chunk)
            temp_pdf.flush()

            markdown_text = pymupdf4llm.to_markdown(temp_pdf.name)
            print(
                f"[DEBUG] Markdown extraction success: {markdown_text[:100]}"
            )  # デバッグ

        # Markdown を JSON で返す
        response_data = {
            "markdown": markdown_text,
        }
        print(f"[DEBUG] Final response: {response_data}")  # デバッグ
        return Response({"markdown": markdown_text}, status=status.HTTP_200_OK)


class TestPDFView(APIView):
    def get(self, request, *args, **kwargs):
        try:
            # publicディレクトリのa.pdfへのパスを設定
            pdf_path = os.path.join("public", "b.pdf")

            # ファイルが存在するか確認
            if not os.path.exists(pdf_path):
                return Response(
                    {"error": "PDF file not found."}, status=status.HTTP_404_NOT_FOUND
                )

            # リクエストのパラメータを取得
            action = request.query_params.get("action", "markdown")
            print(f"[DEBUG] Action: {action}")  # デバッグ

            if action == "llama":
                # 使用例4: LlamaIndex用のドキュメント抽出
                llama_reader = pymupdf4llm.LlamaMarkdownReader()
                llama_docs = llama_reader.load_data(pdf_path)
                return Response(
                    {
                        "llama_docs_count": len(llama_docs),
                        "first_doc_preview": (
                            llama_docs[0].text[:500] if llama_docs else ""
                        ),
                    },
                    status=status.HTTP_200_OK,
                )

            elif action == "images":
                # 使用例5: 画像を抽出
                md_text_images = pymupdf4llm.to_markdown(
                    doc=pdf_path,
                    pages=[1, 11],
                    page_chunks=True,
                    write_images=True,
                    image_path="images",
                    image_format="png",
                    dpi=300,
                )
                return Response(
                    {"images_info": md_text_images[0]["images"]},
                    status=status.HTTP_200_OK,
                )

            elif action == "chunks":
                # 使用例6: データをチャンク化してメタデータ付きで抽出
                md_text_chunks = pymupdf4llm.to_markdown(
                    doc=pdf_path,
                    pages=[0, 1, 2],
                    page_chunks=True,
                )
                return Response(
                    {"first_chunk": md_text_chunks[0]}, status=status.HTTP_200_OK
                )

            elif action == "words":
                # 使用例7: 単語ごとの詳細な抽出
                md_text_words = pymupdf4llm.to_markdown(
                    doc=pdf_path,
                    pages=[1, 2],
                    page_chunks=True,
                    write_images=True,
                    image_path="images",
                    image_format="png",
                    dpi=300,
                    extract_words=True,
                )
                return Response(
                    {"first_words": md_text_words[0]["words"][:5]},
                    status=status.HTTP_200_OK,
                )

            elif action == "tables":
                # 使用例8: 表を抽出
                md_text_tables = pymupdf4llm.to_markdown(
                    doc=pdf_path,
                    pages=[1],
                )
                return Response({"tables": md_text_tables}, status=status.HTTP_200_OK)

            else:
                # デフォルト: Markdown形式で抽出
                md_text = pymupdf4llm.to_markdown(pdf_path)
                return Response(
                    {"markdown_preview": md_text[:500]}, status=status.HTTP_200_OK
                )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# パターン2
# from django.shortcuts import render
# import tempfile
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.parsers import MultiPartParser, FormParser
# from rest_framework import status
# import fitz  # PyMuPDF
# import pytesseract
# from PIL import Image, ImageEnhance
# import io

# class UploadPDFView(APIView):
#     parser_classes = (MultiPartParser, FormParser)

#     def preprocess_image(self, image):
#         """OCRの前処理: 画像をグレースケール化して二値化"""
#         image = image.convert("L")  # グレースケール化
#         enhancer = ImageEnhance.Contrast(image)
#         image = enhancer.enhance(2.0)
#         return image.point(lambda x: 0 if x < 128 else 255)  # 二値化

#     def post(self, request, *args, **kwargs):
#         file_obj = request.FILES.get('file')

#         if not file_obj:
#             return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

#         markdown_text = ""
#         issues = []

#         with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as temp_pdf:
#             for chunk in file_obj.chunks():
#                 temp_pdf.write(chunk)
#             temp_pdf.flush()

#             try:
#                 doc = fitz.open(temp_pdf.name)
#                 ocr_text = ""
#                 for page_num in range(len(doc)):
#                     page = doc[page_num]
#                     pix = page.get_pixmap(dpi=300)
#                     img_bytes = pix.tobytes("png")
#                     image = Image.open(io.BytesIO(img_bytes))
#                     preprocessed_image = self.preprocess_image(image)

#                     # OCRでテキストを抽出
#                     page_text = pytesseract.image_to_string(preprocessed_image, lang="jpn")
#                     ocr_text += f"\n=== Page {page_num + 1} ===\n{page_text}"
#                 markdown_text = ocr_text
#                 print(f"[DEBUG] OCR extraction success")
#             except Exception as e:
#                 issues.append(str(e))
#                 print(f"[DEBUG] OCR extraction failed: {str(e)}")

#         return Response({"markdown": markdown_text, "issues": issues}, status=status.HTTP_200_OK)


# パターン3
# from django.shortcuts import render
# import tempfile
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.parsers import MultiPartParser, FormParser
# from rest_framework import status
# import fitz  # PyMuPDF
# import pytesseract
# from PIL import Image, ImageEnhance
# import io

# class UploadPDFView(APIView):
#     parser_classes = (MultiPartParser, FormParser)

#     def preprocess_image(self, image):
#         """OCRの前処理: 画像をグレースケール化して二値化"""
#         # グレースケール変換
#         image = image.convert("L")
#         # コントラストを強調
#         enhancer = ImageEnhance.Contrast(image)
#         image = enhancer.enhance(2.0)
#         # 二値化処理
#         threshold = 128
#         image = image.point(lambda p: p > threshold and 255)
#         return image

#     def post(self, request, *args, **kwargs):
#         file_obj = request.FILES.get('file')

#         if not file_obj:
#             return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

#         extracted_text = ""
#         issues = []

#         # 一時ファイルにPDFを保存
#         with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as temp_pdf:
#             for chunk in file_obj.chunks():
#                 temp_pdf.write(chunk)
#             temp_pdf.flush()

#             try:
#                 # PDFを開く
#                 doc = fitz.open(temp_pdf.name)
#                 for page_num in range(len(doc)):
#                     page = doc[page_num]
#                     pix = page.get_pixmap(dpi=300)  # DPIを上げて高解像度にする
#                     img_bytes = pix.tobytes("png")
#                     image = Image.open(io.BytesIO(img_bytes))

#                     # OCR前処理
#                     preprocessed_image = self.preprocess_image(image)

#                     # OCRを適用 (日本語指定)
#                     page_text = pytesseract.image_to_string(
#                         preprocessed_image,
#                         lang="jpn",
#                         config="--psm 6"  # 表形式などに対応するセグメンテーションモード
#                     )
#                     extracted_text += f"\n=== Page {page_num + 1} ===\n{page_text}\n"
#                     print(f"[DEBUG] Page {page_num + 1} OCR success")

#             except Exception as e:
#                 issues.append(f"OCR extraction failed: {str(e)}")
#                 print(f"[DEBUG] OCR extraction failed: {str(e)}")

#         response_data = {
#             "ocr_text": extracted_text.strip(),
#             "issues": issues,
#         }
#         print(f"[DEBUG] Final response: {response_data}")
#         return Response(response_data, status=status.HTTP_200_OK)
