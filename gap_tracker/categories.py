"""Fixed US category scope; navigation tracking parameters do not affect identity."""
CATEGORIES = {
    "women-jeans": ("Women / Jeans", "5664", "136", "women/jeans"),
    "women-tshirts-tanks": ("Women / T-Shirts & Tanks", "17076", "136", "women/t-shirts-and-tanks"),
    "men-jeans": ("Men / Jeans", "6998", "75", "men/jeans"),
    "men-tshirts": ("Men / T-Shirts", "5225", "75", "men/t-shirts"),
}


def category_config(key):
    label, cid, department, path = CATEGORIES[key]
    return {"category_key": key, "category": label, "category_id": cid,
            "department_id": department,
            "source_url": f"https://www.gap.com/browse/{path}?cid={cid}"}
