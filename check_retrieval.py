from rag import RetrievalError, retrieve


QUESTIONS = (
    ("Waterfall", "What waterfall is in Dambri Ecotourism Park near Bảo Lộc?", "G01"),
    ("City lake", "Which lake in central Bảo Lộc has a walkable perimeter and lakeside cafés?", "G04"),
    ("Silkworms", "What do silkworms in Bảo Lộc eat, and what do they produce for the silk industry?", "G11"),
    ("Waterfall paraphrase", "Which cascade is the main attraction in the Đamb’ri nature park near Bảo Lộc?", "G01"),
)


def main():
    all_found = True
    for label, question, expected in QUESTIONS:
        try:
            results = retrieve(question)
        except RetrievalError as error:
            print(f"{label}: expected {expected}. Retrieval unavailable. {error}")
            return 1
        scores = ", ".join(f"{item['entry']['id']} ({item['score']:.4f})" for item in results)
        found = any(item["entry"]["id"] == expected for item in results)
        all_found = all_found and found
        print(f"{label}: expected {expected}; actual {scores}. {'Found.' if found else 'Missing.'}")
    return 0 if all_found else 1


if __name__ == "__main__":
    raise SystemExit(main())
