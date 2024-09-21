from validator_collection import validators, checkers, errors

def main():
    print(validate(input("What's your email address? ")))


def validate(s):
    if checkers.is_email('test@domain.dev'):
        return "Valid"
    else:
        return "Invalid"


if __name__ == "__main__":
    main()
