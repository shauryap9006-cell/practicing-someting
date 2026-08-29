import React, { useRef, useMemo, useEffect, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useGLTF, Stars, Cloud, Clouds } from '@react-three/drei';
import { CorridorGrassField } from './GrassField';

// ----------------------------------------------------
// 0. MOUNT FUJI GLB MODEL (Background Mountain)
// ----------------------------------------------------
function MountFuji() {
  const { scene } = useGLTF('/models/mount_fuji.glb');
  const ref = useRef<THREE.Group>(null);

  const cloned = useMemo(() => scene.clone(true), [scene]);

  return (
    <group ref={ref} position={[3, -58, -240]} rotation={[0, 0.2, 0]} scale={[0.022, 0.022, 0.022]}>
      <primitive object={cloned} />
    </group>
  );
}
useGLTF.preload('/models/mount_fuji.glb');

// ----------------------------------------------------
// 0b. VOLUMETRIC CLOUD LAYER  (from portfolio Cloud.tsx)
// ----------------------------------------------------
function SingleCloud({
  initX,
  y,
  z,
  speed,
  seed,
  scale,
}: {
  initX: number;
  y: number;
  z: number;
  speed: number;
  seed: number;
  scale: number;
}) {
  const ref = useRef<THREE.Group>(null);

  useFrame((_s, delta) => {
    if (!ref.current) return;
    ref.current.position.x += delta * speed;
    if (ref.current.position.x > 110) ref.current.position.x = -110;
  });

  return (
    <group ref={ref} position={[initX, y, z]}>
      <Clouds material={THREE.MeshBasicMaterial} frustumCulled={false}>
        <Cloud
          seed={seed}
          segments={40}
          bounds={[8, 1.5, 8]}
          volume={6}
          smallestVolume={0.3}
          concentrate="outside"
          growth={4}
          scale={scale}
          speed={0.12}
          fade={12}
          color="#ffffff"
        />
      </Clouds>
    </group>
  );
}

function CloudLayer() {
  return (
    <>
      {/* Row 1 — higher, slower, bigger */}
      <SingleCloud initX={-80} y={22} z={-100} speed={0.30} seed={2}  scale={1.6} />
      <SingleCloud initX={ 15} y={25} z={-120} speed={0.22} seed={9}  scale={1.4} />
      <SingleCloud initX={ 75} y={21} z={-85}  speed={0.40} seed={17} scale={1.8} />
      {/* Row 2 — slightly lower, faster, smaller */}
      <SingleCloud initX={-40} y={18} z={-60}  speed={0.55} seed={5}  scale={1.2} />
      <SingleCloud initX={ 45} y={16} z={-55}  speed={0.65} seed={11} scale={1.0} />
      <SingleCloud initX={-95} y={20} z={-70}  speed={0.45} seed={23} scale={1.3} />
    </>
  );
}


// ----------------------------------------------------
// 1. HIGH-CONTRAST VANDE BHARAT & RAJDHANI TRAIN RAKES
// ----------------------------------------------------
function TrainCoach({
  position,
  isLocomotive = false,
  isReverse = false,
  theme = 'vande_bharat',
}: {
  position: [number, number, number];
  isLocomotive?: boolean;
  isReverse?: boolean;
  theme?: 'vande_bharat' | 'rajdhani';
}) {
  const coachLength = isLocomotive ? 8.2 : 7.6;
  const coachWidth = 1.1;
  const coachHeight = 1.15;

  const isVande = theme === 'vande_bharat';
  const bodyColor = isVande ? '#E6E9F0' : '#8B1E1E'; // Crisp Silver/White or Deep Crimson Red
  const stripeColor = isVande ? '#152E66' : '#FFB224'; // Deep Royal Blue or Golden Amber
  const speedStripeColor = '#FF9900'; // Bright Indian Railways safety orange

  return (
    <group position={position} rotation={[0, isReverse ? Math.PI : 0, 0]}>
      {/* Main Coach Body */}
      <mesh position={[0, coachHeight / 2 + 0.25, 0]}>
        <boxGeometry args={[coachWidth, coachHeight, coachLength]} />
        <meshStandardMaterial
          color={bodyColor}
          metalness={0.5}
          roughness={0.25}
        />
      </mesh>

      {/* Aerodynamic Primary Livery Stripe */}
      <mesh position={[0, coachHeight / 2 + 0.15, 0]}>
        <boxGeometry args={[coachWidth + 0.03, 0.28, coachLength + 0.02]} />
        <meshStandardMaterial
          color={stripeColor}
          metalness={0.4}
          roughness={0.3}
        />
      </mesh>

      {/* Thin Gold/Amber Speed Stripe */}
      <mesh position={[0, coachHeight / 2 + 0.35, 0]}>
        <boxGeometry args={[coachWidth + 0.04, 0.06, coachLength + 0.02]} />
        <meshStandardMaterial
          color={speedStripeColor}
          emissive={speedStripeColor}
          emissiveIntensity={0.8}
        />
      </mesh>

      {/* Aerodynamic Bullet/Locomotive Nose */}
      {isLocomotive && (
        <group position={[0, coachHeight / 2 + 0.25, coachLength / 2]}>
          {/* Sloped front nose wedge */}
          <mesh position={[0, -0.05, 1.1]} rotation={[0.4, 0, 0]}>
            <boxGeometry args={[coachWidth * 0.96, coachHeight * 0.85, 2.2]} />
            <meshStandardMaterial color={bodyColor} metalness={0.6} roughness={0.2} />
          </mesh>

          {/* Front Blue / Red Livery Wrap on Nose */}
          <mesh position={[0, -0.12, 1.3]} rotation={[0.4, 0, 0]}>
            <boxGeometry args={[coachWidth * 0.98, 0.45, 1.9]} />
            <meshStandardMaterial color={stripeColor} metalness={0.5} roughness={0.2} />
          </mesh>

          {/* Driver Cockpit Windshield (Glossy Tinted Glass) */}
          <mesh position={[0, 0.32, 0.8]} rotation={[0.5, 0, 0]}>
            <boxGeometry args={[coachWidth * 0.88, 0.42, 0.8]} />
            <meshStandardMaterial
              color="#0A1118"
              metalness={0.9}
              roughness={0.1}
            />
          </mesh>

          {/* High-Intensity Dual LED Projector Headlights */}
          <mesh position={[-0.35, -0.15, 2.0]}>
            <sphereGeometry args={[0.09, 16, 16]} />
            <meshBasicMaterial color="#FFFFFF" />
          </mesh>
          <mesh position={[0.35, -0.15, 2.0]}>
            <sphereGeometry args={[0.09, 16, 16]} />
            <meshBasicMaterial color="#FFFFFF" />
          </mesh>

          {/* Forward Track Lighting Cones */}
          <pointLight color="#FFF8E0" intensity={12} distance={35} position={[0, 0.3, 3.5]} />
          <spotLight
            color="#FFF4D0"
            intensity={16}
            distance={50}
            angle={0.45}
            penumbra={0.5}
            position={[0, 0.5, 2.0]}
            target-position={[0, -0.5, 35]}
          />
        </group>
      )}

      {/* Bright Glowing Passenger Windows along Coaches */}
      {!isLocomotive && (
        <group position={[0, coachHeight / 2 + 0.32, 0]}>
          {[-2.6, -1.7, -0.8, 0.1, 1.0, 1.9, 2.8].map((z, wIdx) => (
            <React.Fragment key={wIdx}>
              {/* Left Window */}
              <mesh position={[-coachWidth / 2 - 0.02, 0, z]}>
                <boxGeometry args={[0.04, 0.36, 0.65]} />
                <meshStandardMaterial
                  color="#FFE8A0"
                  emissive="#FFB224"
                  emissiveIntensity={1.8}
                  roughness={0.1}
                />
              </mesh>
              {/* Right Window */}
              <mesh position={[coachWidth / 2 + 0.02, 0, z]}>
                <boxGeometry args={[0.04, 0.36, 0.65]} />
                <meshStandardMaterial
                  color="#FFE8A0"
                  emissive="#FFB224"
                  emissiveIntensity={1.8}
                  roughness={0.1}
                />
              </mesh>
            </React.Fragment>
          ))}
          {/* Warm Interior Ambient Glow casting outside */}
          <pointLight color="#FFB224" intensity={2.5} distance={7} position={[0, 0, 0]} />
        </group>
      )}

      {/* Roof AC Units & Aerodynamic Modules */}
      <mesh position={[0, coachHeight + 0.32, -1.8]}>
        <boxGeometry args={[0.75, 0.16, 2.2]} />
        <meshStandardMaterial color="#4A4E58" roughness={0.5} />
      </mesh>
      <mesh position={[0, coachHeight + 0.32, 1.8]}>
        <boxGeometry args={[0.75, 0.16, 2.2]} />
        <meshStandardMaterial color="#4A4E58" roughness={0.5} />
      </mesh>

      {/* Roof Pantograph on Locomotive */}
      {isLocomotive && (
        <group position={[0, coachHeight + 0.35, -2.0]}>
          {/* Base */}
          <mesh position={[0, 0.06, 0]}>
            <boxGeometry args={[0.7, 0.08, 1.0]} />
            <meshStandardMaterial color="#30333A" />
          </mesh>
          {/* Articulated Lower Arm */}
          <mesh position={[0, 0.5, -0.25]} rotation={[-0.6, 0, 0]}>
            <cylinderGeometry args={[0.025, 0.025, 1.0, 8]} />
            <meshStandardMaterial color="#6A6F7C" metalness={0.9} />
          </mesh>
          {/* Upper Reach Arm */}
          <mesh position={[0, 1.05, 0.2]} rotation={[0.6, 0, 0]}>
            <cylinderGeometry args={[0.02, 0.02, 1.0, 8]} />
            <meshStandardMaterial color="#6A6F7C" metalness={0.9} />
          </mesh>
          {/* Catenary Contact Strip */}
          <mesh position={[0, 1.48, 0.55]}>
            <boxGeometry args={[1.0, 0.04, 0.2]} />
            <meshStandardMaterial color="#FFB224" emissive="#FFB224" emissiveIntensity={0.8} />
          </mesh>
          {/* Subtle Electric Spark at Catenary Contact */}
          <pointLight color="#88D4FF" intensity={3} distance={4} position={[0, 1.5, 0.55]} />
        </group>
      )}

      {/* Wheel Bogies (Underbody) */}
      <group position={[0, 0.14, -coachLength / 2 + 1.4]}>
        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[coachWidth * 0.9, 0.15, 1.7]} />
          <meshStandardMaterial color="#181B20" metalness={0.8} />
        </mesh>
        <mesh position={[-coachWidth / 2 + 0.05, 0, -0.5]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.24, 0.24, 0.1, 14]} />
          <meshStandardMaterial color="#555A66" metalness={0.9} />
        </mesh>
        <mesh position={[coachWidth / 2 - 0.05, 0, -0.5]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.24, 0.24, 0.1, 14]} />
          <meshStandardMaterial color="#555A66" metalness={0.9} />
        </mesh>
        <mesh position={[-coachWidth / 2 + 0.05, 0, 0.5]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.24, 0.24, 0.1, 14]} />
          <meshStandardMaterial color="#555A66" metalness={0.9} />
        </mesh>
        <mesh position={[coachWidth / 2 - 0.05, 0, 0.5]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.24, 0.24, 0.1, 14]} />
          <meshStandardMaterial color="#555A66" metalness={0.9} />
        </mesh>
      </group>

      <group position={[0, 0.14, coachLength / 2 - 1.4]}>
        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[coachWidth * 0.9, 0.15, 1.7]} />
          <meshStandardMaterial color="#181B20" metalness={0.8} />
        </mesh>
        <mesh position={[-coachWidth / 2 + 0.05, 0, -0.5]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.24, 0.24, 0.1, 14]} />
          <meshStandardMaterial color="#555A66" metalness={0.9} />
        </mesh>
        <mesh position={[coachWidth / 2 - 0.05, 0, -0.5]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.24, 0.24, 0.1, 14]} />
          <meshStandardMaterial color="#555A66" metalness={0.9} />
        </mesh>
        <mesh position={[-coachWidth / 2 + 0.05, 0, 0.5]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.24, 0.24, 0.1, 14]} />
          <meshStandardMaterial color="#555A66" metalness={0.9} />
        </mesh>
        <mesh position={[coachWidth / 2 - 0.05, 0, 0.5]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.24, 0.24, 0.1, 14]} />
          <meshStandardMaterial color="#555A66" metalness={0.9} />
        </mesh>
      </group>
    </group>
  );
}

// Multi-Coach Train Rake
function FullTrainRake({
  isReverse = false,
  theme = 'vande_bharat',
}: {
  isReverse?: boolean;
  theme?: 'vande_bharat' | 'rajdhani';
}) {
  return (
    <group>
      {/* Coach 0: Front Bullet Locomotive */}
      <TrainCoach position={[0, 0, 0]} isLocomotive={true} isReverse={isReverse} theme={theme} />
      {/* Coach 1: AC Executive Car */}
      <TrainCoach position={[0, 0, isReverse ? 8.4 : -8.4]} isReverse={isReverse} theme={theme} />
      {/* Coach 2: AC Chair Car */}
      <TrainCoach position={[0, 0, isReverse ? 16.4 : -16.4]} isReverse={isReverse} theme={theme} />
      {/* Coach 3: AC Chair Car */}
      <TrainCoach position={[0, 0, isReverse ? 24.4 : -24.4]} isReverse={isReverse} theme={theme} />
    </group>
  );
}

// ----------------------------------------------------
// 2. STEEL TRACKS, POLISHED RAILS & BALLAST
// ----------------------------------------------------
function CorridorTracks() {
  const sleepers = useMemo(() => {
    const items = [];
    for (let z = -140; z < 140; z += 1.0) {
      items.push(z);
    }
    return items;
  }, []);

  return (
    <group position={[0, -0.4, -40]}>
      {/* Ballast Gravel Bed with Sloped Shoulders */}
      <mesh position={[0, -0.15, 0]} receiveShadow>
        <boxGeometry args={[6.8, 0.24, 280]} />
        <meshStandardMaterial color="#22242B" roughness={0.92} metalness={0.08} />
      </mesh>

      {/* UP Line Rails (Left Track) */}
      <mesh position={[-1.45, 0.12, 0]}>
        <boxGeometry args={[0.08, 0.18, 280]} />
        <meshStandardMaterial color="#9AA4B8" metalness={0.95} roughness={0.12} />
      </mesh>
      <mesh position={[-0.35, 0.12, 0]}>
        <boxGeometry args={[0.08, 0.18, 280]} />
        <meshStandardMaterial color="#9AA4B8" metalness={0.95} roughness={0.12} />
      </mesh>

      {/* DOWN Line Rails (Right Track) */}
      <mesh position={[0.35, 0.12, 0]}>
        <boxGeometry args={[0.08, 0.18, 280]} />
        <meshStandardMaterial color="#9AA4B8" metalness={0.95} roughness={0.12} />
      </mesh>
      <mesh position={[1.45, 0.12, 0]}>
        <boxGeometry args={[0.08, 0.18, 280]} />
        <meshStandardMaterial color="#9AA4B8" metalness={0.95} roughness={0.12} />
      </mesh>

      {/* Concrete Sleepers */}
      {sleepers.map((z, i) => (
        <group key={i} position={[0, 0, z]}>
          <mesh position={[-0.9, 0, 0]}>
            <boxGeometry args={[1.7, 0.12, 0.28]} />
            <meshStandardMaterial color="#2E323B" roughness={0.8} />
          </mesh>
          <mesh position={[0.9, 0, 0]}>
            <boxGeometry args={[1.7, 0.12, 0.28]} />
            <meshStandardMaterial color="#2E323B" roughness={0.8} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

// ----------------------------------------------------
// 3. CATENARY MASTS & OVERHEAD 25kV WIRE
// ----------------------------------------------------
function CatenaryOverhead() {
  const poles = useMemo(() => {
    const arr = [];
    for (let z = -120; z < 120; z += 20) {
      arr.push(z);
    }
    return arr;
  }, []);

  return (
    <group position={[0, -0.4, -40]}>
      {/* 25kV Contact Wires */}
      <mesh position={[-0.9, 4.0, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.012, 0.012, 280, 6]} />
        <meshStandardMaterial color="#FFB224" emissive="#FFB224" emissiveIntensity={0.6} />
      </mesh>
      <mesh position={[0.9, 4.0, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.012, 0.012, 280, 6]} />
        <meshStandardMaterial color="#FFB224" emissive="#FFB224" emissiveIntensity={0.6} />
      </mesh>

      {/* Catenary Mast Structures */}
      {poles.map((z, i) => (
        <group key={i} position={[0, 0, z]}>
          {/* Steel Mast */}
          <mesh position={[-2.8, 2.4, 0]}>
            <boxGeometry args={[0.16, 4.8, 0.16]} />
            <meshStandardMaterial color="#3E424C" metalness={0.7} />
          </mesh>
          {/* Cantilever Arm */}
          <mesh position={[-0.9, 4.3, 0]}>
            <boxGeometry args={[3.8, 0.1, 0.1]} />
            <meshStandardMaterial color="#3E424C" metalness={0.7} />
          </mesh>
          {/* Insulators */}
          <mesh position={[-0.9, 4.15, 0]}>
            <cylinderGeometry args={[0.05, 0.05, 0.25, 8]} />
            <meshStandardMaterial color="#B07D38" roughness={0.3} />
          </mesh>
          <mesh position={[0.9, 4.15, 0]}>
            <cylinderGeometry args={[0.05, 0.05, 0.25, 8]} />
            <meshStandardMaterial color="#B07D38" roughness={0.3} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

// ----------------------------------------------------
// 4. SIGNALS & LIGHTING
// ----------------------------------------------------
function SignalsAndLighting() {
  return (
    <group position={[0, -0.4, -40]}>
      {/* Signal Post 1: Clear Green */}
      <group position={[-2.6, 2.8, -10]}>
        <mesh position={[0, -1.4, 0]}>
          <cylinderGeometry args={[0.05, 0.05, 2.8, 8]} />
          <meshStandardMaterial color="#2B2E36" />
        </mesh>
        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[0.25, 0.6, 0.18]} />
          <meshStandardMaterial color="#111317" />
        </mesh>
        <mesh position={[0, 0.15, 0.1]}>
          <sphereGeometry args={[0.08, 16, 16]} />
          <meshBasicMaterial color="#3ECF8E" />
        </mesh>
        <pointLight color="#3ECF8E" intensity={6} distance={18} position={[0, 0.15, 0.3]} />
      </group>

      {/* Signal Post 2: Caution Amber */}
      <group position={[-2.6, 2.8, -60]}>
        <mesh position={[0, -1.4, 0]}>
          <cylinderGeometry args={[0.05, 0.05, 2.8, 8]} />
          <meshStandardMaterial color="#2B2E36" />
        </mesh>
        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[0.25, 0.6, 0.18]} />
          <meshStandardMaterial color="#111317" />
        </mesh>
        <mesh position={[0, -0.08, 0.1]}>
          <sphereGeometry args={[0.08, 16, 16]} />
          <meshBasicMaterial color="#FFB224" />
        </mesh>
        <pointLight color="#FFB224" intensity={6} distance={18} position={[0, -0.08, 0.3]} />
      </group>
    </group>
  );
}

// ----------------------------------------------------
// 5. MOVING TRAINS & GRASS INTEGRATION
// ----------------------------------------------------
function CorridorSceneContent({ mousePos }: { mousePos: { x: number; y: number } }) {
  const train1Ref = useRef<THREE.Group>(null);
  const train2Ref = useRef<THREE.Group>(null);

  const train1WorldPos = useRef(new THREE.Vector3(-0.9, -0.4, -30));
  const train2WorldPos = useRef(new THREE.Vector3(0.9, -0.4, 10));

  const mouseWorldPos = useRef(new THREE.Vector3(0, 0, 0));
  const isMouseActive = useRef(false);

  const { camera, raycaster } = useThree();
  const groundPlane = useMemo(() => new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), []);
  const planeHit = useMemo(() => new THREE.Vector3(), []);
  const ndcMouse = useMemo(() => new THREE.Vector2(), []);

  useFrame((state, delta) => {
    // Train 1: Vande Bharat Express (Approaching on Left Track)
    if (train1Ref.current) {
      train1Ref.current.position.z += delta * 24;
      if (train1Ref.current.position.z > 50) {
        train1Ref.current.position.z = -150;
      }
      train1WorldPos.current.copy(train1Ref.current.position);
    }

    // Train 2: Rajdhani Express (Receding on Right Track)
    if (train2Ref.current) {
      train2Ref.current.position.z -= delta * 20;
      if (train2Ref.current.position.z < -150) {
        train2Ref.current.position.z = 50;
      }
      train2WorldPos.current.copy(train2Ref.current.position);
    }

    // Raycast mouse to ground plane
    ndcMouse.set(mousePos.x, mousePos.y);
    raycaster.setFromCamera(ndcMouse, camera);
    if (raycaster.ray.intersectPlane(groundPlane, planeHit)) {
      mouseWorldPos.current.copy(planeHit);
      isMouseActive.current = true;
    }

    // Smooth camera motion with parallax
    const targetX = -0.6 + mousePos.x * 0.8;
    const targetY = 2.5 + mousePos.y * 0.45;
    state.camera.position.x = THREE.MathUtils.lerp(state.camera.position.x, targetX, 0.05);
    state.camera.position.y = THREE.MathUtils.lerp(state.camera.position.y, targetY, 0.05);
    state.camera.lookAt(1.4, 0.4, -20);
  });

  return (
    <>
      {/* Ambient & Scene Lighting — neutral night palette */}
      <ambientLight intensity={1.0} color="#C8CDD8" />
      <directionalLight position={[-30, 45, 25]} intensity={2.2} color="#FFF8E0" castShadow />
      <directionalLight position={[30, 25, -20]} intensity={0.6} color="#4A5568" />
      <pointLight position={[-1, 8, 0]} intensity={3} distance={50} color="#FFFFFF" />

      {/* Mount Fuji — Far Background Mountain */}
      <MountFuji />

      {/* Night Sky Stars — regular field */}
      <Stars
        radius={180}
        depth={70}
        count={8000}
        factor={3.5}
        saturation={0.1}
        fade
        speed={0.4}
      />
      {/* Bright accent stars — fewer but much larger & warmer */}
      <Stars
        radius={160}
        depth={50}
        count={300}
        factor={8}
        saturation={0.6}
        fade
        speed={0.2}
      />

      {/* Moving Cloud Layer */}
      <CloudLayer />

      {/* Diagonal Corridor Group (South-West to South-East sweep) */}
      <group position={[-0.5, 0, -5]} rotation={[0, 0.52, 0]}>
        {/* 1. Procedural Lush Grassland Flanking the Tracks */}
        <CorridorGrassField
          train1Pos={train1WorldPos.current}
          train2Pos={train2WorldPos.current}
          mouseWorldPos={mouseWorldPos.current}
          isMouseActive={isMouseActive.current}
        />

        {/* 2. Ballast Gravel & Rails */}
        <CorridorTracks />

        {/* 3. Overhead 25kV Electrification */}
        <CatenaryOverhead />

        {/* 4. Moving Trains */}
        <group ref={train1Ref} position={[-0.9, -0.4, -30]}>
          <FullTrainRake theme="vande_bharat" />
        </group>

        <group ref={train2Ref} position={[0.9, -0.4, 10]}>
          <FullTrainRake isReverse={true} theme="rajdhani" />
          {/* Red Rear Marker Lights */}
          <pointLight color="#FF2200" intensity={8} distance={20} position={[0, 0.6, 2.5]} />
        </group>

        {/* 5. Block Signals & Lamps */}
        <SignalsAndLighting />
      </group>
    </>
  );
}

// ----------------------------------------------------
// 6. MAIN EXPORT COMPONENT
// ----------------------------------------------------
export function ThreeCorridor() {
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [hasWebGL, setHasWebGL] = useState(true);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mediaQuery.matches);

    const checkWebGL = () => {
      try {
        const canvas = document.createElement('canvas');
        return !!(
          window.WebGLRenderingContext &&
          (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
        );
      } catch {
        return false;
      }
    };
    setHasWebGL(checkWebGL());

    const handleMouseMove = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth) * 2 - 1;
      const y = -(e.clientY / window.innerHeight) * 2 + 1;
      setMousePos({ x, y });
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  if (!hasWebGL || reducedMotion) {
    return (
      <div className="absolute inset-0 z-0 overflow-hidden bg-[#0E0F11] flex items-center justify-center opacity-70 pointer-events-none">
        <svg viewBox="0 0 1000 600" className="w-full h-full object-cover">
          <line x1="100" y1="600" x2="500" y2="280" stroke="#4A4E58" strokeWidth="3" />
          <line x1="900" y1="600" x2="500" y2="280" stroke="#4A4E58" strokeWidth="3" />
          <circle cx="500" cy="280" r="3" fill="#FFB224" opacity="0.8" />
          <circle cx="480" cy="310" r="2" fill="#3ECF8E" opacity="0.9" />
        </svg>
      </div>
    );
  }

  return (
    <div className="absolute inset-0 z-0 overflow-hidden bg-[#050505]">
      <Canvas
        camera={{ position: [-0.6, 2.5, 9.0], fov: 48 }}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
        dpr={[1, 1.5]}
      >
        <color attach="background" args={['#050505']} />
        <fog attach="fog" args={['#050505', 80, 500]} />

        <CorridorSceneContent mousePos={mousePos} />
      </Canvas>

      {/* Cinematic Meadow Vignette */}
      <div className="absolute inset-0 bg-gradient-to-t from-[#0E0F11] via-transparent to-[#0E0F11]/30 pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-r from-[#0E0F11]/80 via-transparent to-transparent pointer-events-none w-1/2" />
    </div>
  );
}
