const { Sequelize, DataTypes } = require('sequelize');
require('dotenv').config();

const sequelize = new Sequelize(process.env.DB_NAME, process.env.DB_USER, process.env.DB_PASSWORD, {
  host: process.env.DB_HOST,
  dialect: process.env.DB_DIALECT
});

// Define User model
const User = sequelize.define('User', {
  username: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true
  },
  password: {
    type: DataTypes.STRING,
    allowNull: false
  },
  email: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true
  }
}, {
  tableName: 'users',
  freezeTableName: true,
  timestamps: true
});

// Define Card model
const Card = sequelize.define('Card', {
  name: {
    type: DataTypes.STRING,
    allowNull: false
  },
  strength: {
    type: DataTypes.INTEGER,
    allowNull: false,
    validate: { min: 0 }
  },
  speed: {
    type: DataTypes.INTEGER,
    allowNull: false,
    validate: { min: 0 }
  },
  life: {
    type: DataTypes.INTEGER,
    allowNull: false, 
    validate: { min: 0 }
  },
  threshold: {
    type: DataTypes.STRING
  },
  cost: {
    type: DataTypes.INTEGER,
    allowNull: false,
    validate: { min: 0 }
  },
  extra_cost: {
    type: DataTypes.TEXT
  },
  description: {
    type: DataTypes.TEXT
  },
  flip_up: {
    type: DataTypes.INTEGER,
    validate: { min: 0 }
  },
  flip_up_threshold: {
    type: DataTypes.STRING
  }
}, {
  tableName: 'cards',
  freezeTableName: true,
  timestamps: true
});

// Define Deck model
const Deck = sequelize.define('Deck', {
  userId: {
    type: DataTypes.INTEGER,
    allowNull: false,
    references: {
      model: 'users',
      key: 'id'
    }
  },
  name: {
    type: DataTypes.STRING
  },
  createdAt: {
    type: DataTypes.DATE,
    defaultValue: Sequelize.NOW
  }
}, {
  tableName: 'decks',
  freezeTableName: true,
  timestamps: true
});

// Define DeckCard model
const DeckCard = sequelize.define('DeckCard', {
  deckId: {
    type: DataTypes.INTEGER,
    references: {
      model: 'decks',
      key: 'id'
    }
  },
  cardId: {
    type: DataTypes.INTEGER,
    references: {
      model: 'cards',
      key: 'id'
    }
  },
  quantity: {
    type: DataTypes.INTEGER
  }
}, {
  tableName: 'deck_cards',
  freezeTableName: true,
  timestamps: true
});

module.exports = {
  sequelize,
  User,
  Card,
  Deck,
  DeckCard
};

