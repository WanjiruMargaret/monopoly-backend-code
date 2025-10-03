from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, Player, Property, Card, GameState
from game_logic import roll_dice_logic, buy_property_logic, apply_card_logic