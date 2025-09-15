'use client';

import { useEffect, useMemo, useState } from 'react';
import { Room, RoomEvent } from 'livekit-client';
import { motion } from 'motion/react';
import {
  RoomAudioRenderer,
  RoomContext,
  StartAudio,
} from '@livekit/components-react';
import { toastAlert } from '@/components/alert-toast';
import { SessionView } from '@/components/session-view';
import { Toaster } from '@/components/ui/sonner';
import { Welcome } from '@/components/welcome';
import type { AppConfig } from '@/lib/types';

const MotionWelcome = motion.create(Welcome);
const MotionSessionView = motion.create(SessionView);

interface AppProps {
  appConfig: AppConfig;
}

export function App({ appConfig }: AppProps) {
  const room = useMemo(() => new Room(), []);
  const [sessionStarted, setSessionStarted] = useState(false);

  // ✅ Fetch token + URL from FastAPI backend
  const getConnectionDetails = async (identity: string) => {
    const resp = await fetch(
      `http://127.0.0.1:8000/get-token?identity=${identity}`
    );
    if (!resp.ok) {
      throw new Error(`Failed to fetch token: ${resp.status}`);
    }
    const data = await resp.json();
    return {
      serverUrl: data.url,
      participantToken: data.token,
    };
  };

  useEffect(() => {
    const onDisconnected = () => {
      setSessionStarted(false);
    };

    const onMediaDevicesError = (error: Error) => {
      toastAlert({
        title: 'Encountered an error with your media devices',
        description: `${error.name}: ${error.message}`,
      });
    };

    room.on(RoomEvent.MediaDevicesError, onMediaDevicesError);
    room.on(RoomEvent.Disconnected, onDisconnected);

    return () => {
      room.off(RoomEvent.Disconnected, onDisconnected);
      room.off(RoomEvent.MediaDevicesError, onMediaDevicesError);
    };
  }, [room]);

  useEffect(() => {
    let aborted = false;

    const startSession = async () => {
      // 1️⃣ Generate a unique identity per session
      const identity = `frontend-user_${Math.floor(Math.random() * 10000)}`;

      try {
        // 2️⃣ Disconnect previous session if it exists
        if (room.state !== 'disconnected') {
          await room.disconnect();
          // Small delay to ensure LiveKit server cleans up
          await new Promise((res) => setTimeout(res, 500));
        }

        // 3️⃣ Fetch new token from backend
        const connectionDetails = await getConnectionDetails(identity);

        // 4️⃣ Connect to LiveKit
        await room.connect(connectionDetails.serverUrl, connectionDetails.participantToken);

        // 5️⃣ Enable microphone after connection
        await room.localParticipant.setMicrophoneEnabled(true, undefined, {
          preConnectBuffer: appConfig.isPreConnectBufferEnabled,
        });

        if (!aborted) setSessionStarted(true);
      } catch (error: any) {
        if (aborted) return;
        toastAlert({
          title: 'Error connecting to LiveKit',
          description: `${error.name}: ${error.message}`,
        });
      }
    };

    if (sessionStarted) {
      startSession();
    }

    return () => {
      aborted = true;
      room.disconnect().catch(() => {});
    };
  }, [sessionStarted, room, appConfig.isPreConnectBufferEnabled]);

  const { startButtonText } = appConfig;

  return (
    <main>
      <MotionWelcome
        key="welcome"
        startButtonText={startButtonText}
        onStartCall={() => setSessionStarted(true)}
        disabled={sessionStarted}
        initial={{ opacity: 1 }}
        animate={{ opacity: sessionStarted ? 0 : 1 }}
        transition={{
          duration: 0.5,
          ease: 'linear',
          delay: sessionStarted ? 0 : 0.5,
        }}
      />

      <RoomContext.Provider value={room}>
        <RoomAudioRenderer />
        <StartAudio label="Start Audio" />
        <MotionSessionView
          key="session-view"
          appConfig={appConfig}
          disabled={!sessionStarted}
          sessionStarted={sessionStarted}
          initial={{ opacity: 0 }}
          animate={{ opacity: sessionStarted ? 1 : 0 }}
          transition={{
            duration: 0.5,
            ease: 'linear',
            delay: sessionStarted ? 0.5 : 0,
          }}
        />
      </RoomContext.Provider>

      <Toaster />
    </main>
  );
}
