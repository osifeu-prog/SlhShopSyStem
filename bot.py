# -*- coding: utf-8 -*-
import os
import logging
from typing import Optional, Dict, Any, List

import httpx
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

