<template>
  <div id="app">
    <h1>Spoils CCG Online Client</h1>
    <p>Backend status: {{ backendStatus }}</p>
    <button @click="startGame" :disabled="gameState !== null">Start Game</button>
    
    <div v-if="gameState">
      <h2>Turn: {{ gameState.turn }} | Current Player: {{ gameState.current_player }} | Phase: {{ gameState.phase }}</h2>
      
      <div v-for="(player, playerName) in gameState.players" :key="playerName">
        <h3>{{ playerName }} {{ playerName === gameState.current_player ? '(Active)' : '' }}</h3>
        <p>Faction: {{ player.faction ? player.faction.name : 'None' }}</p>
        <h4>Resources: {{ player.resources.length }}</h4>
        <h4>Attached Resources: {{ player.attached_resources.length }}</h4>
        <h4>Hand:</h4>
        <ul>
          <li v-for="card in player.hand" :key="card.name">
            {{ card.name }} ({{ card.type }}, Cost: {{ card.cost }}, Threshold: {{ card.threshold }})
            <button 
              @click="playCard(playerName, card.name)" 
              :disabled="playerName !== gameState.current_player || gameState.phase !== 'main' || card.type === 'Resource'"
            >
              Play
            </button>
          </li>
        </ul>
        <h4>In Play:</h4>
        <ul>
          <li v-for="card in player.in_play" :key="card.name">
            {{ card.name }} ({{ card.type }})
          </li>
        </ul>
        <h4>Discard Pile: {{ player.discard.length }} cards</h4>
        <h4>Removed from Game: {{ player.removed.length }} cards</h4>
      </div>
      
      <div v-if="gameState.current_player === 'player1' || gameState.current_player === 'player2'">
        <div v-if="gameState.waiting_for_start_action">
          <button @click="chooseStartAction('draw')">Draw a Card</button>
          <button @click="chooseStartAction('resource')">Play a Resource</button>
        </div>
        <div v-if="gameState.waiting_for_resource_selection">
          <h4>Select a card to play as resource:</h4>
          <ul>
            <li v-for="card in gameState.players[gameState.current_player].hand" :key="card.name">
              {{ card.name }} ({{ card.type }})
              <button 
                @click="playResource(card.name, true)" 
                :disabled="card.type !== 'Resource'"
              >
                Play Face Up
              </button>
              <button @click="playResource(card.name, false)">
                Play Face Down
              </button>
            </li>
          </ul>
          <button @click="cancelResourceSelection">Cancel</button>
        </div>
        <div v-if="gameState.phase === 'main'">
          <h4>Additional Actions:</h4>
          <button @click="drawCard" :disabled="gameState.players[gameState.current_player].resources.length < 3">
            Draw a Card (Cost: 3)
          </button>
          <button @click="initiateAdditionalResource" :disabled="gameState.players[gameState.current_player].resources.length < 4">
            Play Additional Resource (Cost: 4)
          </button>
          <button @click="endTurn">End Turn</button>
        </div>

        <div v-if="selectingAdditionalResource">
          <h4>Select a card to play as additional resource:</h4>
          <ul>
            <li v-for="card in gameState.players[gameState.current_player].hand" :key="card.name">
              {{ card.name }} ({{ card.type }})
              <button @click="playAdditionalResource(card.name, true)" :disabled="card.type !== 'Resource'">
                Play Face Up
              </button>
              <button @click="playAdditionalResource(card.name, false)">
                Play Face Down
              </button>
            </li>
          </ul>
          <button @click="cancelAdditionalResource">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import io from 'socket.io-client';

export default {
  name: 'App',
  data() {
    return {
      backendStatus: 'Checking...',
      gameState: null,
      socket: null,
      selectingAdditionalResource: false
    };
  },
  mounted() {
    this.checkBackendStatus();
    this.connectWebSocket();
  },
  methods: {
    checkBackendStatus() {
      fetch('http://localhost:5000/api/health')
        .then(response => response.json())
        .then(data => {
          this.backendStatus = data.status;
        })
        .catch(error => {
          this.backendStatus = 'Error connecting to backend';
          console.error('Error:', error);
        });
    },
    connectWebSocket() {
      this.socket = io('http://localhost:5000');
      this.socket.on('game_update', (data) => {
        this.gameState = data;
      });
    },
    startGame() {
      fetch('http://localhost:5000/api/start_game', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
          this.gameState = data.state;
        })
        .catch(error => console.error('Error:', error));
    },
    chooseStartAction(action) {
      fetch('http://localhost:5000/api/choose_start_action', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action }),
      })
        .then(response => response.json())
        .then(data => {
          if (data.error) {
            console.error(data.error);
          } else {
            this.gameState = data.state;
          }
        })
        .catch(error => console.error('Error:', error));
    },
    playResource(cardName, faceUp) {
      fetch('http://localhost:5000/api/play_resource', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ card: cardName, face_up: faceUp }),
      })
        .then(response => response.json())
        .then(data => {
          if (data.error) {
            console.error(data.error);
          } else {
            this.gameState = data.state;
          }
        })
        .catch(error => console.error('Error:', error));
    },
    cancelResourceSelection() {
      fetch('http://localhost:5000/api/cancel_resource_selection', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
          if (data.error) {
            console.error(data.error);
          } else {
            this.gameState = data.state;
          }
        })
        .catch(error => console.error('Error:', error));
    },
    playCard(player, cardName) {
      fetch('http://localhost:5000/api/play_card', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ player, card: cardName }),
      })
        .then(response => response.json())
        .then(data => {
          if (data.error) {
            console.error(data.error);
          } else {
            this.gameState = data.state;
          }
        })
        .catch(error => console.error('Error:', error));
    },
    endTurn() {
      fetch('http://localhost:5000/api/end_turn', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
          this.gameState = data.state;
        })
        .catch(error => console.error('Error:', error));
    },
    drawCard() {
      fetch('http://localhost:5000/api/draw_card', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
          if (data.error) {
            console.error(data.error);
          } else {
            this.gameState = data.state;
          }
        })
        .catch(error => console.error('Error:', error));
    },
    initiateAdditionalResource() {
      this.selectingAdditionalResource = true;
    },
    playAdditionalResource(cardName, faceUp) {
      fetch('http://localhost:5000/api/play_additional_resource', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ card: cardName, face_up: faceUp }),
      })
        .then(response => response.json())
        .then(data => {
          if (data.error) {
            console.error(data.error);
          } else {
            this.gameState = data.state;
            this.selectingAdditionalResource = false;
          }
        })
        .catch(error => console.error('Error:', error));
    },
    cancelAdditionalResource() {
      this.selectingAdditionalResource = false;
    }
  }
};
</script>
