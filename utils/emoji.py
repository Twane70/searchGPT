def get_png_url(char: str) -> str:
    """ Pulled from: https://github.com/glasnt/emojificate/blob/latest/emojificate/filter.py"""

    cdn_fmt = "https://twemoji.maxcdn.com/v/latest/72x72/{codepoint}.png"

    def codepoint(codes):
        # See https://github.com/twitter/twemoji/issues/419#issuecomment-637360325
        if "200d" not in codes:
            return "-".join([c for c in codes if c != "fe0f"])
        return "-".join(codes)

    return cdn_fmt.format(codepoint=codepoint(["{cp:x}".format(cp=ord(c)) for c in char]))