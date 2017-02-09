# -*- coding: utf-8 -*-
#! /usr/bin/env python3
import email
from email.parser import BytesParser
from email import policy
import os
import subprocess

from customSettings import SERVER_SETS

"""
    ###################
    This simple script is designed to automaticaly encrypt your chosen mail messages of particular mail dirs 
    at your mail server(Postfix).
    This script uses CLI tool gpg2 and it(script) works localy at the srver.
    ###################

    SERVER_SETS is main custom settings which are separated to another python file customSettings.py which is 
    at the same level as this script. Also, must be blank file '__init__.py alongside these files at the same dir.'
    So you need to import this settings: 'from customSettings import SERVER_SETS'.
    Or if you want all in one script just define this variable here and remove 'from customSettings import SERVER_SETS'.
    Example of SERVER_SETS is below:

    SERVER_SETS = {
    "/path/to/my/mail.com":{
        "ACCOUNTS" : ["justin"],
        "EMAIL_DIRS" : ["cur"],
        "boundary" : "8kjkgKkjfgJhLJL3mMk6pnTeNrhR",
        "public_keys" : ["896716TM"]
    },
    "/path/to/another/somemail.com":{
        "ACCOUNTS" : ["sam", "john"],
        "EMAIL_DIRS" : ["cur", "new", ".Sent"],
        "boundary" : "8kjkgKkjfgJhLJLklk::LK:5KJKHl",
        "public_keys" : ["896716TM", "651234VD"]
    },
    ......
}

"""
#### This is example of setting's variable. If you want have all in one script, it should be uncomented and 
#    filled with your actual settings.
#
# SERVER_SETS = {
#     "/path/to/my/mail.com":{
#         "ACCOUNTS" : ["justin"],
#         "EMAIL_DIRS" : ["cur"],
#         "boundary" : "8kjkgKkjfgJhLJL3mMk6pnTeNrhR",
#         "public_keys" : ["896716TM"]
#     },
#     "/path/to/another/somemail.com":{
#         "ACCOUNTS" : ["sam", "john"],
#         "EMAIL_DIRS" : ["cur", "new", ".Sent"],
#         "boundary" : "8kjkgKkjfgJhLJLklk::LK:5KJKHl",
#         "public_keys" : ["896716TM", "651234VD"]
#     }
# 
# }

WRAPPER = """To: Master <me@mail.com>
From: Some Persone <someone@mail.com>
Message-ID: <5b8ae902-81f9-3e05-2731-14e042974f07@mail.com>
Subject: This is Subject
Date: Sat, 21 Jan 2017 13:42:03 +0200
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:45.0) Gecko/20100101
 Thunderbird/45.6.0
MIME-Version: 1.0
Content-Type: multipart/encrypted;
 protocol="application/pgp-encrypted";
 boundary="{0}"

This is an OpenPGP/MIME encrypted message (RFC 4880 and 3156)
--{0}
Content-Type: application/pgp-encrypted
Content-Description: PGP/MIME version identification

Version: 1

--{0}
Content-Type: application/octet-stream; name="encrypted.asc"
Content-Description: OpenPGP encrypted message
Content-Disposition: inline; filename="encrypted.asc"


"""

headers_list = ["to", "from", "message-id", "subject", "date"]


commands = {
    "encrypt_message" : "gpg2 --batch --yes -e -a{0} {1}",
    "append_encrypted_message": "cat {encrypted} >> {message} && echo '{boundary_last}' >> {message} && rm {encrypted}"
}

boundary_last =lambda boundary: "--{}--".format(boundary)
asc_filename = lambda m: m + ".asc"

def get_recipients_with_arg(public_keys):
    recipients_with_arg = ""
    for key in public_keys: recipients_with_arg+=" -r {}".format(key)
    return recipients_with_arg


def get_messages(SERVER_SETS):
    for domain in SERVER_SETS.keys():
        for account in SERVER_SETS[domain]["ACCOUNTS"]:
            for email_dir in SERVER_SETS[domain]["EMAIL_DIRS"]:
                email_dir_path = os.path.join(domain, account, email_dir)
                print("EMAIL_DIRECTORY=========>\n", email_dir_path, "\n================")
                for msg_file in os.listdir(email_dir_path):
                    messagePath = os.path.join(email_dir_path, msg_file)
                    if os.path.isfile(messagePath):
                        msg = read_email_file(messagePath)
                        original_headers = get_original_headers(msg)
                        print(original_headers)
                        if not is_encrypted(msg):
                            yield (messagePath, SERVER_SETS[domain]["boundary"], SERVER_SETS[domain]["public_keys"], original_headers)
                        else:
                            print("Skipped! This message is already encrypted.")


def read_email_file(messagePath):
    with open(messagePath, "rb") as f:
        print("Prarsing...")
        msg = BytesParser(policy=policy.default).parse(f)
    return msg


def is_encrypted(parsedMessage):
    content_type = parsedMessage["Content-Type"]
    print("Content-Type: ", content_type)
    if content_type and "multipart/encrypted" in content_type.lower():return True
    else: return False


def get_original_headers(parsedMessage):
    headers = {
        "to" : parsedMessage["To"],
        "from" : parsedMessage["From"],
        "message-id" : parsedMessage["Message-ID"],
        "subject" : parsedMessage["Subject"],
        "date" : parsedMessage["Date"]
    }
    return headers

def write_wrapper_head(messagePath, WRAPPER, boundary):
    with open(messagePath, "w") as f:
        f.write(WRAPPER.format(boundary))

def execute_shell_command(command):
    subprocess.call(command, shell=True)


def main():
    messages_sets = get_messages(SERVER_SETS)
    for i,msg_set in enumerate(messages_sets):
        if i < 4:continue
        msg_filename = msg_set[0]
        print(msg_filename)
        encrypt_command = commands["encrypt_message"].format(get_recipients_with_arg(msg_set[2]), msg_filename)
        execute_shell_command(encrypt_command)
        write_wrapper_head(msg_filename, WRAPPER, msg_set[1])
        append_command = commands["append_encrypted_message"].format(encrypted=asc_filename(msg_filename),
                                                                    message=msg_filename,
                                                                    boundary_last=boundary_last(msg_set[1]))
        execute_shell_command(append_command)
        msg = read_email_file(msg_filename)
        original_headers = msg_set[3]
        for header in headers_list:
            if header in [key.lower() for key in msg.keys()]:
                msg.replace_header(header, original_headers[header])
            else:
                msg[header] = original_headers[header]
        with open(msg_filename, "w") as f:
            f.write(msg.as_string())

        print("Message is saved.")


if __name__ == "__main__":
    main()