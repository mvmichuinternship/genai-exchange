from modules.document_parser import DocumentParser

if __name__ == "__main__":
    parser = DocumentParser()
    parsed = parser.parse("sample.pdf")  # or sample.docx/xml

    print("Source:", parsed.source)
    print("Metadata:", parsed.metadata)
    print("First chunk:", parsed.content[0])
