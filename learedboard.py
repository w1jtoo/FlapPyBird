from json import dump, load
import os

def get_file_name() -> str:
    return os.path.join(os.path.dirname(__file__), "./public/score.json")

def serialize_to_file(items) -> None:
    with open(get_file_name(), "w") as f:
        dump(items, f)


def get_score_from_file() -> list:
    with open(get_file_name()) as f:
        return list(load(f))


def save_score(name: str, img: str, score: int) -> None:
    scores = get_score_from_file()

    found = False
    for info in scores:
        if info["name"] == name:
            if score > info["score"]:
                info["score"] = score

            found = True
            break
    if not found:
        scores.append({"name": name, "score": score, "img": img})

    serialize_to_file(scores)
