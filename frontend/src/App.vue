<template>
  <div id="app">
    <h1>Spoils CCG Online Client</h1>
    <p>Backend status: {{ backendStatus }}</p>
    <button @click="startGame" :disabled="gameState !== null">Start Game</button>
    
    <div v-if="gameState" class="game-container">
      <div v-for="playerName in ['player1', 'player2']" :key="playerName" class="player-side">
        <h2>{{ playerName }} {{ playerName === gameState.current_player ? '(Active)' : '' }}</h2>
        <p>Turn: {{ gameState.turn }} | Phase: {{ gameState.phase }}</p>
        <p>Faction: {{ gameState.players[playerName].faction ? gameState.players[playerName].faction.name : 'None' }}</p>
        
        <div>
          <h3>Resources: {{ gameState.players[playerName].resources.length }}</h3>
          <h3>Attached Resources: {{ gameState.players[playerName].attached_resources.length }}</h3>
        </div>
        
        <div>
          <h3>Hand:</h3>
          <ul>
            <li v-for="card in gameState.players[playerName].hand" :key="card.name">
              {{ card.name }} ({{ card.type }}, Cost: {{ card.cost }}, Threshold: {{ card.threshold }})
              <button 
                @click="playCard(playerName, card.name)" 
                :disabled="playerName !== gameState.active_player || 
                           (gameState.current_player !== playerName && 
                            card.type !== 'Tactic' && 
                            !card.keywords.includes('TACTICAL'))"
              >
                Play
              </button>
            </li>
          </ul>
        </div>
        
        <div>
          <h3>In Play:</h3>
          <ul>
            <li v-for="card in gameState.players[playerName].in_play" :key="card.name">
              {{ card.name }} ({{ card.type }})
            </li>
          </ul>
        </div>
        
        <div>
          <h3>Discard Pile: {{ gameState.players[playerName].discard.length }} cards</h3>
          <h3>Removed from Game: {{ gameState.players[playerName].removed.length }} cards</h3>
        </div>
        
        <div>
          <h4>Additional Actions:</h4>
          <button @click="drawCard(playerName)" :disabled="gameState.players[playerName].resources.length < 3">
            Draw a Card (Cost: 3)
          </button>
          <button @click="initiateAdditionalResource(playerName)" :disabled="gameState.players[playerName].resources.length < 4">
            Play Additional Resource (Cost: 4)
          </button>
        </div>
        
        <div v-if="gameState.current_player === playerName">
          <div v-if="gameState.waiting_for_start_action">
            <button @click="chooseStartAction('draw')">Draw a Card</button>
            <button @click="chooseStartAction('resource')">Play a Resource</button>
          </div>
          
          <div v-if="gameState.waiting_for_resource_selection">
            <h4>Select a card to play as resource:</h4>
            <ul>
              <li v-for="card in gameState.players[playerName].hand" :key="card.name">
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
          
          <button @click="endTurn" :disabled="gameState.waiting_for_response">End Turn</button>
        </div>
        
        <div v-if="selectingAdditionalResource === playerName">
          <h4>Select a card to play as additional resource:</h4>
          <ul>
            <li v-for="card in gameState.players[playerName].hand" :key="card.name">
              {{ card.name }} ({{ card.type }})
              <button @click="playAdditionalResource(playerName, card.name, true)" :disabled="card.type !== 'Resource'">
                Play Face Up
              </button>
              <button @click="playAdditionalResource(playerName, card.name, false)">
                Play Face Down
              </button>
            </li>
          </ul>
          <button @click="cancelAdditionalResource">Cancel</button>
        </div>
        
        <div v-if="gameState.waiting_for_response && gameState.active_player === playerName">
          <h3>Respond to Action</h3>
          <button @click="respond('NO_RESPONSE')">No Response</button>
          <button @click="respond('RESPONSE')">Respond</button>
        </div>
      </div>
    </div>
    
    <div v-if="gameState && gameState.action_stack.length > 0">
      <h3>Action Stack:</h3>
      <ul>
        <li v-for="(action, index) in gameState.action_stack" :key="index">
          {{ action.type }} by {{ action.player }}: {{ action.card ? action.card.name : 'N/A' }}
        </li>
      </ul>
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
      selectingAdditionalResource: null
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
drawCard(player) {
  console.log(`Attempting to draw card for ${player}`);
  fetch('http://localhost:5000/api/draw_card', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ player: player }),
  })
    .then(response => {
      console.log('Response status:', response.status);
      return response.json();
    })
    .then(data => {
      if (data.error) {
        console.error(data.error);
      } else {
        console.log(`Card drawn successfully for ${player}`);
        this.gameState = data.state;
      }
    })
    .catch(error => console.error('Error:', error));
},    
    initiateAdditionalResource(player) {
      this.selectingAdditionalResource = player;
    },
    playAdditionalResource(player, cardName, faceUp) {
      fetch('http://localhost:5000/api/play_additional_resource', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ player, card: cardName, face_up: faceUp }),
      })
        .then(response => response.json())
        .then(data => {
          if (data.error) {
            console.error(data.error);
          } else {
            this.gameState = data.state;
            this.selectingAdditionalResource = null;
          }
        })
        .catch(error => console.error('Error:', error));
    },
    cancelAdditionalResource() {
      this.selectingAdditionalResource = null;
    },
    respond(response) {
      fetch('http://localhost:5000/api/respond', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ player: this.gameState.active_player, response }),
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
    }
  }
};
</script>

<style scoped>
.game-container {
  display: flex;
  justify-content: space-between;
}

.player-side {
  width: 48%;
  border: 1px solid #ccc;
  padding: 10px;
  margin: 10px 0;
}
</style>
