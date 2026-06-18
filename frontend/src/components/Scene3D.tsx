import { Canvas, useFrame } from '@react-three/fiber';
import { useRef, useMemo } from 'react';
import * as THREE from 'three';

function Particles() {
  const ref = useRef<THREE.Points>(null);
  const count = 300;

  const positions = useMemo(() => {
    const p = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      p[i * 3] = (Math.random() - 0.5) * 28;
      p[i * 3 + 1] = (Math.random() - 0.5) * 28;
      p[i * 3 + 2] = (Math.random() - 0.5) * 18;
    }
    return p;
  }, []);

  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * 0.012;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial color="#6d9fff" size={0.025} transparent opacity={0.4} sizeAttenuation depthWrite={false} />
    </points>
  );
}

function Ring() {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    ref.current.rotation.x = clock.getElapsedTime() * 0.05;
    ref.current.rotation.z = clock.getElapsedTime() * 0.03;
  });
  return (
    <mesh ref={ref} position={[5, 1, -6]}>
      <torusGeometry args={[2, 0.04, 16, 64]} />
      <meshBasicMaterial color="#a78bfa" wireframe transparent opacity={0.06} />
    </mesh>
  );
}

function Ico() {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    ref.current.rotation.y = clock.getElapsedTime() * 0.04;
    ref.current.rotation.x = clock.getElapsedTime() * 0.025;
  });
  return (
    <mesh ref={ref} position={[-4, -1, -5]}>
      <icosahedronGeometry args={[1.6, 1]} />
      <meshBasicMaterial color="#6d9fff" wireframe transparent opacity={0.035} />
    </mesh>
  );
}

export default function Scene3D() {
  return (
    <div className="canvas-bg">
      <Canvas camera={{ position: [0, 0, 10], fov: 50 }} dpr={[1, 1.5]} gl={{ alpha: true, antialias: true }}>
        <Particles />
        <Ring />
        <Ico />
      </Canvas>
    </div>
  );
}
