import re
def is_adress(address):
    return re.match(r"^(0x)?[0-9a-fA-F]{40}$", address)

def is_twitter(twitter):
    return re.match("[\\\/\@\:\,]",twitter)

def is_facebook(facebook):
    return re.match(r"www\.facebook\.com/\w+",facebook)

def is_twitter_repost(facebook):
    return re.match(r"www\.twitter\.com/\w+",facebook)

def is_email(email):
    return re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)",email)
