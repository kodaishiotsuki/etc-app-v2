import tempfile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import status
from django.shortcuts import render
import pymupdf4llm
import pytesseract
from pdf2image import convert_from_path
import logging
import os
from markdownify import markdownify as md
import pandas as pd
from django.http import HttpResponse
import io
from rest_framework.renderers import JSONRenderer


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s"
)


# パターンB
class UploadPDFView(APIView):
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    renderer_classes = (JSONRenderer,)

    def options(self, request, *args, **kwargs):
        response = Response()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = (
            "Content-Type, Accept, X-Requested-With"
        )
        return response

    def post(self, request, *args, **kwargs):
        try:
            file_obj = request.FILES.get("file")
            output_format = request.data.get(
                "format", "markdown"
            )  # 出力形式を指定（デフォルトはmarkdown）

            if not file_obj:
                logger.error("No file uploaded")
                return Response(
                    {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
                )

            logger.debug(f"Request headers: {request.headers}")
            logger.debug(f"Output format: {output_format}")

            markdown_text = ""
            formatted_data = []  # エクセル出力用のデータを保存

            # 一時ファイルとして保存して処理
            with tempfile.NamedTemporaryFile(delete=True) as temp_pdf:
                logger.debug("Saving uploaded file to temporary location")
                for chunk in file_obj.chunks():
                    temp_pdf.write(chunk)
                temp_pdf.flush()
                logger.debug(f"Temporary file created at {temp_pdf.name}")

                # PDFからテキストを抽出
                raw_text = pymupdf4llm.to_markdown(temp_pdf.name)

                # テキストを解析して新しい形式に変換
                lines = raw_text.split("\n")
                formatted_lines = []

                # 新しいヘッダーを追加
                headers = [
                    "カード番号",
                    "利用月",
                    "利用年月日",
                    "車種",
                    "車両番号",
                    "入口IC",
                    "出口IC",
                    "割引前の金額",
                    "割引後の金額",
                ]
                formatted_lines.append("| " + " | ".join(headers) + " |")
                formatted_lines.append("|" + "---|" * len(headers))

                # データ行を処理
                for line in lines:
                    if (
                        "|" in line
                        and not line.startswith("|---")
                        and not "利用年月日" in line
                    ):
                        parts = line.strip().split("|")
                        if len(parts) >= 5:
                            try:
                                # 日付とIC情報を分解
                                date_ic_info = parts[1].strip().split()
                                if len(date_ic_info) >= 5:
                                    # 日付を20240902形式に変換
                                    date_parts = date_ic_info[0].split(
                                        "/"
                                    )  # 23/04/01 を分割
                                    year = f"20{date_parts[0]}"  # 23 → 2023
                                    month = date_parts[1].zfill(2)  # 4 → 04
                                    day = date_parts[2].zfill(2)  # 1 → 01
                                    formatted_date = f"{year}{month}{day}"
                                    month_number = str(int(date_parts[1]))  # 04 → 4

                                    # ICの情報を抽出
                                    # 時刻とIC情報を分離
                                    ic_info = []
                                    for i, x in enumerate(date_ic_info):
                                        # 時刻（HH:MM形式）や日付（YY/MM/DD形式）は除外
                                        if not ":" in x and not "/" in x:
                                            # 数字のみの場合は時刻の一部として除外
                                            if not x.replace(" ", "").isdigit():
                                                ic_info.append(x)

                                    # ICの情報を処理
                                    if len(ic_info) == 1:
                                        # ICが1つの場合は出口ICとして扱う
                                        entry_ic = ""
                                        exit_ic = ic_info[0]
                                    elif len(ic_info) >= 2:
                                        # ICが2つ以上の場合は、最初のICを入口、最後のICを出口として扱う
                                        entry_ic = ic_info[0]
                                        exit_ic = ic_info[-1]
                                    else:
                                        entry_ic = ""
                                        exit_ic = ""

                                    # 自)や至)が含まれている場合は除去
                                    entry_ic = entry_ic.replace("自)", "").strip()
                                    exit_ic = exit_ic.replace("至)", "").strip()

                                # 料金情報を分解
                                fee_info = parts[2].strip().split()
                                # カンマを含む金額を正しく処理
                                if fee_info:
                                    # 割引前料金の処理
                                    # カンマで分割されている場合は結合
                                    if len(fee_info) >= 2 and fee_info[0].endswith(","):
                                        original_fee = (
                                            fee_info[0].rstrip(",") + "," + fee_info[1]
                                        )
                                    else:
                                        original_fee = fee_info[0]
                                    original_fee = original_fee.replace(
                                        "(", ""
                                    ).replace(")", "")

                                    # 割引後料金の処理
                                    # 最後の2つの数字がカンマで分割されている場合は結合
                                    if len(fee_info) >= 2 and fee_info[-2].endswith(
                                        ","
                                    ):
                                        final_fee = (
                                            fee_info[-2].rstrip(",")
                                            + ","
                                            + fee_info[-1]
                                        )
                                    else:
                                        final_fee = fee_info[-1]
                                else:
                                    original_fee = ""
                                    final_fee = ""

                                # 車両情報を分解
                                vehicle_info = parts[4].strip().split()
                                if len(vehicle_info) >= 3:
                                    vehicle_type = vehicle_info[0]
                                    vehicle_number = vehicle_info[1]
                                    card_number = vehicle_info[2]

                                    # 新しい形式で行を追加
                                    formatted_line = f"| {card_number} | {month_number} | {formatted_date} | {vehicle_type} | {vehicle_number} | {entry_ic} | {exit_ic} | {original_fee} | {final_fee} |"
                                    formatted_lines.append(formatted_line)

                                    # エクセル出力用のデータを保存
                                    formatted_data.append(
                                        {
                                            "カード番号": card_number,
                                            "利用月": month_number,
                                            "利用年月日": formatted_date,
                                            "車種": vehicle_type,
                                            "車両番号": vehicle_number,
                                            "入口IC": entry_ic,
                                            "出口IC": exit_ic,
                                            "割引前の金額": original_fee,
                                            "割引後の金額": final_fee,
                                        }
                                    )

                            except Exception as e:
                                logger.warning(f"行の解析中にエラーが発生しました: {e}")
                                continue

                markdown_text = "\n".join(formatted_lines)

            # 出力形式に応じてレスポンスを返す
            if output_format == "excel":
                try:
                    # DataFrameを作成
                    df = pd.DataFrame(formatted_data)

                    # Excelファイルを作成
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                        df.to_excel(writer, index=False, sheet_name="ETCデータ")

                    # レスポンスの作成
                    excel_buffer.seek(0)
                    excel_data = excel_buffer.getvalue()

                    response = HttpResponse(
                        excel_data,
                        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                    response["Content-Disposition"] = (
                        "attachment; filename=etc_data.xlsx"
                    )
                    response["Content-Length"] = len(excel_data)
                    response["Access-Control-Allow-Origin"] = "*"
                    response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
                    response["Access-Control-Allow-Headers"] = (
                        "Content-Type, Accept, X-Requested-With"
                    )
                    response["Access-Control-Expose-Headers"] = "Content-Disposition"
                    return response
                except Exception as excel_error:
                    logger.exception("Error creating Excel file")
                    error_response = Response(
                        {
                            "error": f"Excelファイルの生成に失敗しました: {str(excel_error)}"
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
                    error_response["Access-Control-Allow-Origin"] = "*"
                    error_response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
                    error_response["Access-Control-Allow-Headers"] = (
                        "Content-Type, Accept, X-Requested-With"
                    )
                    return error_response
            else:
                # 従来のMarkdownレスポンス
                response_data = {
                    "markdown": markdown_text,
                }
                response = Response(response_data, status=status.HTTP_200_OK)
                response["Access-Control-Allow-Origin"] = "*"
                response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
                response["Access-Control-Allow-Headers"] = (
                    "Content-Type, Accept, X-Requested-With"
                )
                return response

        except Exception as e:
            logger.exception("An error occurred during file processing")
            error_response = Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            error_response["Access-Control-Allow-Origin"] = "*"
            error_response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            error_response["Access-Control-Allow-Headers"] = (
                "Content-Type, Accept, X-Requested-With"
            )
            return error_response


# パターンA
# class TestPDFView(APIView):
#     def post(self, request, *args, **kwargs):
#         try:
#             file = request.FILES.get("file")
#             if not file:
#                 logger.error("No file provided in the request.")
#                 return Response(
#                     {"error": "ファイルが選択されていません。"},
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )

#             # PDFを一時ファイルに保存
#             pdf_path = "/tmp/temp_uploaded.pdf"
#             with open(pdf_path, "wb") as temp_pdf:
#                 for chunk in file.chunks():
#                     temp_pdf.write(chunk)
#             logger.debug(f"File saved to {pdf_path}")

#             # テキストを抽出
#             extracted_text = self.extract_text_from_pdf(pdf_path)
#             logger.debug(
#                 f"Extracted text: {extracted_text[:100]}..."
#             )  # 最初の100文字をログ

#             # Markdown形式に整形
#             markdown_text = self.format_as_markdown(extracted_text)
#             logger.debug(
#                 f"Formatted Markdown text: {markdown_text[:100]}..."
#             )  # 最初の100文字をログ

#             # Markdown を JSON で返す
#             response_data = {"markdown": markdown_text}
#             logger.info(f"Final response: {response_data}")
#             return Response(response_data, status=status.HTTP_200_OK)

#         except Exception as e:
#             logger.exception("An error occurred during PDF processing.")
#             return Response(
#                 {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )

#     def extract_text_from_pdf(self, pdf_path):
#         """PDFからテキストを抽出（OCR処理を含む）"""
#         text = ""
#         try:
#             images = convert_from_path(pdf_path, dpi=300)
#             logger.debug(f"Converted {len(images)} pages from PDF to images.")
#             for i, image in enumerate(images):
#                 custom_config = r"--oem 3 --psm 6"
#                 page_text = pytesseract.image_to_string(
#                     image, lang="jpn", config=custom_config
#                 )
#                 text += f"--- Page {i + 1} ---\n{page_text}\n"
#                 logger.debug(f"Processed page {i + 1}")
#         except Exception as e:
#             logger.error(f"Error during OCR processing: {e}")
#             raise Exception(f"Error during OCR processing: {e}")
#         return text

#     def format_as_markdown(self, text):
#         """抽出されたテキストをMarkdown形式に変換"""
#         lines = text.split("\n")
#         markdown_lines = []
#         for line in lines:
#             if line.startswith("--- Page"):
#                 markdown_lines.append(f"## {line}")
#             elif line.strip():
#                 markdown_lines.append(line)
#         formatted_text = "\n".join(markdown_lines)
#         logger.debug("Markdown formatting completed.")
#         return formatted_text


class TestPDFView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            file = request.FILES.get("file")
            if not file:
                logger.error("No file provided in the request.")
                return Response(
                    {"error": "ファイルが選択されていません。"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # アップロードされたファイルを一時ファイルとして保存
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                for chunk in file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name
                logger.debug(f"File saved to temporary path: {temp_file_path}")

            # PDFを画像に変換してOCRでテキストを抽出
            extracted_text = self.extract_text_from_pdf(temp_file_path)
            logger.debug(
                f"Extracted text (first 100 characters): {extracted_text[:100]}..."
            )

            # Markdown形式に整形
            markdown_text = self.format_as_markdown(extracted_text)
            logger.debug(
                f"Formatted Markdown text (first 100 characters): {markdown_text[:100]}..."
            )

            # 一時ファイルを削除
            os.remove(temp_file_path)
            logger.debug(f"Temporary file {temp_file_path} deleted.")

            # Markdown を JSON で返す
            response_data = {"markdown": markdown_text}
            logger.info(f"Final response: {response_data}")
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("An error occurred during PDF processing.")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def extract_text_from_pdf(self, pdf_path):
        """PDFからテキストを抽出（OCR処理を含む）"""
        text = ""
        try:
            images = convert_from_path(pdf_path, dpi=300)
            logger.debug(f"Converted {len(images)} pages from PDF to images.")
            for i, image in enumerate(images):
                custom_config = r"--oem 3 --psm 6"
                page_text = pytesseract.image_to_string(
                    image, lang="jpn", config=custom_config
                )
                text += f"--- Page {i + 1} ---\n{page_text}\n"
                logger.debug(f"Processed OCR for page {i + 1}")
        except Exception as e:
            logger.error(f"Error during OCR processing: {e}")
            raise Exception(f"Error during OCR processing: {e}")
        return text

    def format_as_markdown(self, text):
        """抽出されたテキストをMarkdown形式に変換"""
        lines = text.split("\n")
        markdown_lines = []
        for line in lines:
            if line.startswith("--- Page"):
                markdown_lines.append(f"## {line}")
            elif line.strip():
                markdown_lines.append(line)
        formatted_text = "\n".join(markdown_lines)
        logger.debug("Markdown formatting completed.")
        return formatted_text
