import React from 'react';
import { Composition } from 'remotion';
import { PromoVideo } from './PromoVideo';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="KillTheHWPromo"
        component={PromoVideo}
        durationInFrames={1536}
        fps={60}
        width={1920}
        height={1080}
      />
    </>
  );
};
