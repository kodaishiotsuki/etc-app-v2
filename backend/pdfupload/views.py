from django.shortcuts import render
import tempfile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
import pymupdf4llm

class UploadPDFView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')

        if not file_obj:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        # 一時ファイルとして保存して処理
        with tempfile.NamedTemporaryFile(delete=True) as temp_pdf:
            for chunk in file_obj.chunks():
                temp_pdf.write(chunk)
            temp_pdf.flush()
            md_text = pymupdf4llm.to_markdown(temp_pdf.name)

        # Markdown を JSON で返す
        return Response({"markdown": md_text}, status=status.HTTP_200_OK)

