#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.

First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import datetime
import logging
import os
import time
import subprocess
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from helpers.parameters import parse_args, load_config

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


args = parse_args()
DEFAULT_CONFIG_FILE = 'config.yml'
config_file = args.config if args.config else DEFAULT_CONFIG_FILE
parsed_config = load_config(config_file)

TELEGRAM_TOKEN = parsed_config['trading_options']['TELEGRAM_TOKEN']


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def get_logs(update, context):
    """Send a message when the command /start is issued."""
    f = subprocess.Popen(['tail', '-F', 'log.txt'],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    start_time = datetime.datetime.now()
    while True:
        line = f.stdout.readline()
        update.message.reply_text(line.decode("utf-8"))
        if datetime.datetime.now() - start_time > datetime.timedelta(seconds=10):
            break
    f.kill()


def pause_bot(update, context):
    print("TelegramPauseBOT: Trading paused...")
    with open('signals/tgbot_paused.exc', 'a+') as f:
        f.write('yes')
    update.message.reply_text('Trading paused...')


def unpause_bot(update, context):
    print("TelegramPauseBOT: Trading continued...")
    if os.path.isfile("signals/tgbot_paused.exc"):
        os.remove('signals/tgbot_paused.exc')
    update.message.reply_text('Trading continued...')


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)



if __name__ == '__main__':
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TELEGRAM_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("pause_bot", pause_bot))
    dp.add_handler(CommandHandler("unpause_bot", unpause_bot))
    dp.add_handler(CommandHandler("get_logs", get_logs))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    print("TelegramPauseBOT: Starting the bot...")
    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
