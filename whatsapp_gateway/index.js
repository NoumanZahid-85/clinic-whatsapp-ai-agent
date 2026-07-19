import { makeWASocket, useMultiFileAuthState, DisconnectReason } from '@whiskeysockets/baileys';
import qrcode from 'qrcode-terminal';
import axios from 'axios';
import pino from 'pino';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
dotenv.config({ path: join(__dirname, '..', '.env') });

const AI_SERVER_URL = `http://${process.env.AI_SERVER_HOST || '0.0.0.0'}:${process.env.AI_SERVER_PORT || '8000'}`;
const AUTH_DIR = join(__dirname, 'auth_info');
let sock = null, reconnectTimer = null;

async function startBot() {
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
    const logger = pino({ level: 'silent', transport: { target: 'pino/file', options: { destination: join(__dirname, 'baileys.log') } } });

    sock = makeWASocket({ auth: state, printQRInTerminal: false, logger, syncFullHistory: false, markOnlineOnConnect: false });
    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;
        if (qr) {
            console.log('\n=== Scan QR with WhatsApp ===\n');
            qrcode.generate(qr, { small: true });
            console.log('\n============================\n');
        }
        if (connection === 'open') {
            console.log('Connected! AI Server:', AI_SERVER_URL);
        }
        if (connection === 'close') {
            const reason = lastDisconnect?.error?.output?.statusCode;
            if (reason === DisconnectReason.loggedOut) {
                console.log('Logged out. Delete auth_info and restart.');
            } else {
                console.log('Disconnected (reason:', reason, '). Reconnecting in 5s...');
                clearTimeout(reconnectTimer);
                reconnectTimer = setTimeout(startBot, 5000);
            }
        }
    });

    sock.ev.on('messages.upsert', async (msg) => {
        for (const message of msg.messages) {
            if (!message.key || message.key.fromMe) continue;
            const text = message.message?.conversation || message.message?.extendedTextMessage?.text || '';
            if (!text.trim()) continue;
            const sender = message.key.remoteJid;
            console.log('From:', sender, text);
            try {
                const res = await axios.post(`${AI_SERVER_URL}/process-message`,
                    { sender_id: sender, text }, { timeout: 60000 });
                await sock.sendMessage(sender, { text: res.data.reply });
            } catch (err) {
                const fallback = err.code === 'ECONNREFUSED'
                    ? 'AI server is not running. Please start it.'
                    : 'Error processing message. Please try again.';
                await sock.sendMessage(sender, { text: fallback });
            }
        }
    });
}

process.on('SIGINT', () => { clearTimeout(reconnectTimer); sock?.ws.close(); process.exit(0); });
console.log('Starting CityCare Clinic WhatsApp Bot...');
startBot().catch(err => { console.error(err); process.exit(1); });
