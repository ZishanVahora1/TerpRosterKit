def name_validator(first_name_1, last_name_1, first_name_2, last_name_2):
    def normalize_name(name):
        # Remove spaces, apostrophes, and specific suffixes from the name
        suffixes_to_ignore = ["jr.", "jr", "sr.", "sr"]
        name = name.lower().replace(" ", "").replace("'", "")
        for suffix in suffixes_to_ignore:
            name = name.replace(suffix, "")
        return name

    normalized_first_name_1 = normalize_name(first_name_1)
    normalized_last_name_1 = normalize_name(last_name_1)
    normalized_first_name_2 = normalize_name(first_name_2)
    normalized_last_name_2 = normalize_name(last_name_2)

    return (
        normalized_first_name_1 == normalized_first_name_2
        and normalized_last_name_1 == normalized_last_name_2
    )
