import React, { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

// ----------------------------------------------------
// 1. HIGH-PERFORMANCE PROCEDURAL BLADE GEOMETRY
// ----------------------------------------------------
function createBladeGeometry(segments = 4): THREE.BufferGeometry {
  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];

  for (let i = 0; i <= segments; i++) {
    const v = i / segments;
    // Parabolic taper from base to tip: width = 1 - v^2
    const widthFactor = Math.max(0, 1 - v * v);
    const halfWidth = 0.5 * widthFactor;

    if (i === segments) {
      // Blade sharp tip vertex
      positions.push(0, 1.0, 0);
      uvs.push(0.5, 1.0);
    } else {
      // Left and right vertices for current segment
      positions.push(-halfWidth, v, 0);
      positions.push(halfWidth, v, 0);
      uvs.push(0, v);
      uvs.push(1, v);
    }
  }

  // Generate quad indices
  for (let i = 0; i < segments - 1; i++) {
    const row0 = i * 2;
    const row1 = (i + 1) * 2;
    indices.push(row0, row0 + 1, row1);
    indices.push(row0 + 1, row1 + 1, row1);
  }

  // Tip triangle
  const lastRow = (segments - 1) * 2;
  const tipIndex = segments * 2;
  indices.push(lastRow, lastRow + 1, tipIndex);

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geo.setIndex(indices);
  geo.computeVertexNormals();

  return geo;
}

// ----------------------------------------------------
// 2. SHADERS (Adapted from above-the-grassland with train wake dynamics)
// ----------------------------------------------------
const grassVertexShader = /* glsl */ `
  precision highp float;

  attribute vec3 aPosition;
  attribute float aRotation;
  attribute vec2 aScale;
  attribute vec4 aProps; // x: colorVariation, y: windPhase, z: curvature, w: flutterPhase

  uniform float uTime;
  uniform float uWindSpeed;
  uniform float uWindFrequency;
  uniform float uWindStrength;
  uniform vec2 uWindDirection;
  uniform float uGustStrength;
  uniform float uTurbulence;
  uniform float uFlutterStrength;
  uniform vec3 uTrain1Pos;
  uniform vec3 uTrain2Pos;
  uniform vec3 uMousePos;
  uniform float uMouseActive;

  varying vec2 vUv;
  varying float vHeight;
  varying vec3 vWorldPos;
  varying vec3 vNormalOut;
  varying float vColorVar;
  varying float vShimmer;

  void main() {
    vUv = uv;
    vHeight = uv.y;
    vColorVar = aProps.x;

    float bladeWidth = aScale.x;
    float bladeHeight = aScale.y;
    float rot = aRotation;
    float phase = aProps.y;
    float curveFactor = aProps.z;
    float flutterPhase = aProps.w;

    // Local vertex position scaled
    vec3 pos = position;
    pos.x *= bladeWidth;
    pos.y *= bladeHeight;

    // Rotate blade around its local Y axis
    float cosRot = cos(rot);
    float sinRot = sin(rot);
    vec2 rotatedXZ = vec2(
      pos.x * cosRot - pos.z * sinRot,
      pos.x * sinRot + pos.z * cosRot
    );
    pos.x = rotatedXZ.x;
    pos.z = rotatedXZ.y;

    vec3 worldRoot = aPosition;

    // --- WIND SIMULATION (Multi-Harmonic Waves) ---
    vec2 windDir = normalize(uWindDirection);
    vec2 windPerp = vec2(-windDir.y, windDir.x);

    float wave1 = dot(worldRoot.xz, windDir) * uWindFrequency + uTime * uWindSpeed;
    float wave2 = dot(worldRoot.xz, windPerp) * uWindFrequency * 0.85 + uTime * uWindSpeed * 0.32;

    float mainGust = sin(wave1 + phase);
    float secondaryGust = sin(wave1 * 0.37 + wave2 * 0.9 + uTime * uWindSpeed * 0.31 + phase * 0.73) * uGustStrength;
    float turbulence = sin(wave1 * 2.3 - wave2 * 1.7 + uTime * uWindSpeed * 1.9 + phase * 1.37) * uTurbulence;
    float totalWindWave = (mainGust * 0.62 + secondaryGust + turbulence) * uWindStrength;

    // High frequency flutter vibration along blade height
    float flutter = sin(uTime * 5.5 + worldRoot.x * 0.35 + worldRoot.z * 0.22 + vHeight * 2.8 + flutterPhase) * uFlutterStrength;

    // Quadratic bending displacement (stronger at tip)
    float bendCurve = vHeight * vHeight;
    vec2 windDisplacement = windDir * (totalWindWave + flutter) * bendCurve;

    // Natural droop/curvature along blade orientation
    vec2 naturalDroop = vec2(cosRot, sinRot) * curveFactor * bendCurve * 0.4;
    windDisplacement += naturalDroop;

    // --- TRAIN AERODYNAMIC WAKE DISPLACEMENT ---
    // When train 1 (Vande Bharat) or train 2 (Rajdhani) pass by, air wake pushes grass outwards
    vec2 dTrain1 = worldRoot.xz - uTrain1Pos.xz;
    float distT1 = length(dTrain1);
    float wake1 = smoothstep(12.0, 1.5, distT1) * smoothstep(-45.0, 0.0, worldRoot.z - uTrain1Pos.z) * smoothstep(15.0, 0.0, uTrain1Pos.z - worldRoot.z);
    vec2 trainWake1 = normalize(dTrain1 + vec2(0.001)) * wake1 * 1.8 * bendCurve;

    vec2 dTrain2 = worldRoot.xz - uTrain2Pos.xz;
    float distT2 = length(dTrain2);
    float wake2 = smoothstep(12.0, 1.5, distT2) * smoothstep(-45.0, 0.0, worldRoot.z - uTrain2Pos.z) * smoothstep(15.0, 0.0, uTrain2Pos.z - worldRoot.z);
    vec2 trainWake2 = normalize(dTrain2 + vec2(0.001)) * wake2 * 1.8 * bendCurve;

    // --- MOUSE INTERACTIVE DISPLACEMENT ---
    vec2 dMouse = worldRoot.xz - uMousePos.xz;
    float distMouse = length(dMouse);
    float mousePush = smoothstep(5.0, 0.2, distMouse) * uMouseActive;
    vec2 mouseDisp = normalize(dMouse + vec2(0.001)) * mousePush * 1.4 * bendCurve;

    // Combine all displacements
    vec2 totalDisp = windDisplacement + trainWake1 + trainWake2 + mouseDisp;
    pos.x += totalDisp.x;
    pos.z += totalDisp.y;

    // Height compensation: bending pulls the tip downward
    float bendMagnitude = length(totalDisp);
    pos.y -= bendMagnitude * bendMagnitude * 0.18;
    pos.y = max(0.0, pos.y);

    // Final world position
    vec3 finalWorldPos = worldRoot + pos;
    vWorldPos = finalWorldPos;

    // Normal calculation with blade width curvature rounding for soft lighting
    vec3 baseNormal = normalize(vec3(-sinRot * 0.3 + totalDisp.x * 0.5, 1.0 - bendMagnitude * 0.4, cosRot * 0.3 + totalDisp.y * 0.5));
    vNormalOut = baseNormal;

    // Solar shimmer wave factor
    vShimmer = smoothstep(0.35, 0.75, sin(worldRoot.x * 0.12 + worldRoot.z * 0.08 + uTime * 0.55));

    gl_Position = projectionMatrix * modelViewMatrix * vec4(finalWorldPos, 1.0);
  }
`;

const grassFragmentShader = /* glsl */ `
  precision highp float;

  uniform vec3 uGrassColorBottom;
  uniform vec3 uGrassColorTop;
  uniform vec3 uGrassColorAccent;
  uniform vec3 uGrassColorDry;
  uniform vec3 uSunDir;
  uniform float uTranslucency;
  uniform float uSpecularStrength;
  uniform float uSpecularPower;
  uniform float uFresnelStrength;
  uniform float uAmbientStrength;
  uniform float uAoStrength;

  varying vec2 vUv;
  varying float vHeight;
  varying vec3 vWorldPos;
  varying vec3 vNormalOut;
  varying float vColorVar;
  varying float vShimmer;

  void main() {
    float h = clamp(vHeight, 0.0, 1.0);

    // Root-to-tip vertical gradient
    vec3 baseColor = mix(uGrassColorBottom, uGrassColorTop, pow(h, 0.65));

    // Per-blade natural variation (fresh vibrant vs golden dry tufts)
    vec3 variantColor = mix(uGrassColorAccent, uGrassColorDry, vColorVar);
    vec3 albedo = mix(baseColor, variantColor, vColorVar * 0.35);

    // Subtle wind solar shimmer highlights sweeping across the field
    albedo = mix(albedo, uGrassColorAccent * 1.25, vShimmer * 0.25 * h);

    vec3 normal = normalize(vNormalOut);
    vec3 sunDir = normalize(uSunDir);
    vec3 viewDir = normalize(cameraPosition - vWorldPos);

    // Diffuse sunlight term
    float NdotL = clamp(dot(normal, sunDir) * 0.5 + 0.5, 0.0, 1.0);
    float diffuse = NdotL * NdotL * 0.75 + 0.25;

    // Subsurface translucency (backlight glow through blades)
    float backLight = clamp(dot(-viewDir, sunDir) * 0.5 + 0.5, 0.0, 1.0);
    float sss = pow(backLight, 3.0) * uTranslucency * h;

    // Specular sheen along blade gloss
    vec3 halfVec = normalize(viewDir + sunDir);
    float NdotH = clamp(dot(normal, halfVec), 0.0, 1.0);
    float spec = pow(NdotH, uSpecularPower) * uSpecularStrength * h;

    // Fresnel rim lighting at grazing angles
    float fresnel = pow(1.0 - clamp(dot(normal, viewDir), 0.0, 1.0), 3.5) * uFresnelStrength * h;

    // Ambient Occlusion (darkening towards blade ground root)
    float ao = smoothstep(0.0, 0.25, h) * uAoStrength + (1.0 - uAoStrength);

    // Composite final color
    vec3 litColor = albedo * (diffuse + uAmbientStrength) * ao;
    litColor += vec3(0.55, 0.85, 0.25) * sss;
    litColor += vec3(1.0, 0.96, 0.8) * spec;
    litColor += vec3(0.6, 0.85, 0.35) * fresnel;

    gl_FragColor = vec4(litColor, 1.0);
  }
`;

// ----------------------------------------------------
// 3. FLOWER BLADE SHADERS (Yellow & White Wildflowers)
// ----------------------------------------------------
const flowerVertexShader = /* glsl */ `
  attribute vec3 aPosition;
  attribute vec4 aProps; // x: size, y: phase, z: type (0=yellow, 1=white), w: flutter
  uniform float uTime;
  uniform float uWindSpeed;
  uniform float uWindFrequency;
  uniform float uWindStrength;
  uniform vec2 uWindDirection;
  uniform vec3 uTrain1Pos;
  uniform vec3 uTrain2Pos;

  varying vec2 vUv;
  varying float vFlowerType;

  void main() {
    vUv = uv;
    vFlowerType = aProps.z;

    vec3 worldPos = aPosition;
    float phase = aProps.y;
    float size = aProps.x;

    // Wind wave sway for flower head
    vec2 windDir = normalize(uWindDirection);
    float wave = dot(worldPos.xz, windDir) * uWindFrequency + uTime * uWindSpeed;
    float sway = sin(wave + phase) * uWindStrength * 0.45;
    float flutter = sin(uTime * 4.0 + worldPos.x * 0.5 + worldPos.z * 0.3) * 0.08;

    worldPos.x += windDir.x * (sway + flutter);
    worldPos.z += windDir.y * (sway + flutter);

    // Camera-facing billboard quad
    vec3 camRight = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
    vec3 camUp = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);

    vec3 vertexPos = worldPos + (camRight * (position.x * size) + camUp * (position.y * size));
    gl_Position = projectionMatrix * viewMatrix * vec4(vertexPos, 1.0);
  }
`;

const flowerFragmentShader = /* glsl */ `
  varying vec2 vUv;
  varying float vFlowerType;

  void main() {
    // Circular radial flower petal head
    vec2 uvCentered = vUv - vec2(0.5);
    float dist = length(uvCentered);
    if (dist > 0.5) discard;

    // Petal modulation
    float angle = atan(uvCentered.y, uvCentered.x);
    float petals = sin(angle * 6.0) * 0.08 + 0.42;
    if (dist > petals) discard;

    // Center disc vs outer petal color
    vec3 petalColor = vFlowerType < 0.5 ? vec3(1.0, 0.82, 0.15) : vec3(0.96, 0.96, 0.98);
    vec3 centerColor = vec3(0.85, 0.45, 0.08);

    vec3 finalColor = mix(centerColor, petalColor, smoothstep(0.08, 0.22, dist));
    gl_FragColor = vec4(finalColor, 1.0);
  }
`;

// ----------------------------------------------------
// 4. CORRIDOR GRASS FIELD COMPONENT
// ----------------------------------------------------
export interface GrassFieldProps {
  train1Pos?: THREE.Vector3;
  train2Pos?: THREE.Vector3;
  mouseWorldPos?: THREE.Vector3;
  isMouseActive?: boolean;
}

export function CorridorGrassField({
  train1Pos = new THREE.Vector3(0, 0, 0),
  train2Pos = new THREE.Vector3(0, 0, 0),
  mouseWorldPos = new THREE.Vector3(0, 0, 0),
  isMouseActive = false,
}: GrassFieldProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const flowersMeshRef = useRef<THREE.Mesh>(null);

  // Total grass blade count for dense, expansive meadow look
  const bladeCount = 72000;
  const flowerCount = 1800;

  // Blade Geometry & Instanced Attributes setup
  const { grassGeo, uniforms } = useMemo(() => {
    const geo = createBladeGeometry(4);
    const instGeo = new THREE.InstancedBufferGeometry();
    instGeo.index = geo.index;
    instGeo.attributes.position = geo.attributes.position;
    instGeo.attributes.uv = geo.attributes.uv;
    instGeo.attributes.normal = geo.attributes.normal;

    const positions = new Float32Array(bladeCount * 3);
    const rotations = new Float32Array(bladeCount);
    const scales = new Float32Array(bladeCount * 2);
    const props = new Float32Array(bladeCount * 4);

    let idx = 0;
    for (let i = 0; i < bladeCount; i++) {
      // Flank both sides of the corridor with natural density
      const side = Math.random() > 0.5 ? 1 : -1;
      let x = 0;
      const zone = Math.random();

      if (zone < 0.08) {
        // Shoulder weeds right next to gravel ballast bed
        x = side * (2.6 + Math.random() * 0.9);
      } else {
        // Main lush rolling field extending into distance
        const dist = Math.pow(Math.random(), 1.4); // slightly denser near track
        x = side * (3.5 + dist * 48.0);
      }

      // Along corridor length
      const z = -140 + Math.random() * 280;

      // Height terrain undulation
      const terrainHeight =
        Math.sin(x * 0.08 + z * 0.04) * 0.35 +
        Math.cos(x * 0.04 - z * 0.06) * 0.25 -
        0.4;

      positions[idx * 3] = x;
      positions[idx * 3 + 1] = terrainHeight;
      positions[idx * 3 + 2] = z;

      // Random heading rotation
      rotations[idx] = Math.random() * Math.PI * 2;

      // Blade scale (width, height)
      const heightVar = 0.75 + Math.random() * 0.55;
      const widthVar = 0.055 + Math.random() * 0.035;
      scales[idx * 2] = widthVar;
      scales[idx * 2 + 1] = heightVar;

      // Blade properties: color variation, wind phase, curvature, flutter
      props[idx * 4] = Math.random(); // color variation
      props[idx * 4 + 1] = Math.random() * Math.PI * 2; // wind phase
      props[idx * 4 + 2] = (Math.random() - 0.5) * 0.8; // curvature
      props[idx * 4 + 3] = Math.random() * Math.PI * 2; // flutter phase

      idx++;
    }

    instGeo.setAttribute('aPosition', new THREE.InstancedBufferAttribute(positions, 3));
    instGeo.setAttribute('aRotation', new THREE.InstancedBufferAttribute(rotations, 1));
    instGeo.setAttribute('aScale', new THREE.InstancedBufferAttribute(scales, 2));
    instGeo.setAttribute('aProps', new THREE.InstancedBufferAttribute(props, 4));

    const uniformsObj = {
      uTime: { value: 0 },
      uWindSpeed: { value: 1.3 },
      uWindFrequency: { value: 0.075 },
      uWindStrength: { value: 1.25 },
      uWindDirection: { value: new THREE.Vector2(0.85, 0.45).normalize() },
      uGustStrength: { value: 0.45 },
      uTurbulence: { value: 0.22 },
      uFlutterStrength: { value: 0.15 },
      uGrassColorBottom: { value: new THREE.Color('#1B3811') }, // Rich deep earth green root
      uGrassColorTop: { value: new THREE.Color('#688F38') }, // Lush sunlit blade body
      uGrassColorAccent: { value: new THREE.Color('#8AB842') }, // Spring emerald tips
      uGrassColorDry: { value: new THREE.Color('#A89D46') }, // Golden amber meadow tufts
      uSunDir: { value: new THREE.Vector3(-0.6, 0.8, 0.35).normalize() },
      uTranslucency: { value: 0.65 },
      uSpecularStrength: { value: 0.85 },
      uSpecularPower: { value: 36.0 },
      uFresnelStrength: { value: 0.45 },
      uAmbientStrength: { value: 0.35 },
      uAoStrength: { value: 0.75 },
      uTrain1Pos: { value: new THREE.Vector3(0, 0, 0) },
      uTrain2Pos: { value: new THREE.Vector3(0, 0, 0) },
      uMousePos: { value: new THREE.Vector3(0, 0, 0) },
      uMouseActive: { value: 0 },
    };

    return { grassGeo: instGeo, uniforms: uniformsObj };
  }, []);

  // Flower instancing
  const { flowerGeo, flowerUniforms } = useMemo(() => {
    const quadGeo = new THREE.PlaneGeometry(0.22, 0.22);
    const instGeo = new THREE.InstancedBufferGeometry();
    instGeo.index = quadGeo.index;
    instGeo.attributes.position = quadGeo.attributes.position;
    instGeo.attributes.uv = quadGeo.attributes.uv;

    const positions = new Float32Array(flowerCount * 3);
    const props = new Float32Array(flowerCount * 4);

    for (let i = 0; i < flowerCount; i++) {
      const side = Math.random() > 0.5 ? 1 : -1;
      const x = side * (4.2 + Math.random() * 42.0);
      const z = -130 + Math.random() * 260;
      const terrainHeight =
        Math.sin(x * 0.08 + z * 0.04) * 0.35 +
        Math.cos(x * 0.04 - z * 0.06) * 0.25 -
        0.4;
      const bladeHeight = 0.8 + Math.random() * 0.5;

      positions[i * 3] = x;
      positions[i * 3 + 1] = terrainHeight + bladeHeight;
      positions[i * 3 + 2] = z;

      props[i * 4] = 0.75 + Math.random() * 0.5; // size
      props[i * 4 + 1] = Math.random() * Math.PI * 2; // phase
      props[i * 4 + 2] = Math.random() > 0.5 ? 1 : 0; // flower type
      props[i * 4 + 3] = Math.random(); // flutter
    }

    instGeo.setAttribute('aPosition', new THREE.InstancedBufferAttribute(positions, 3));
    instGeo.setAttribute('aProps', new THREE.InstancedBufferAttribute(props, 4));

    const uniformsObj = {
      uTime: { value: 0 },
      uWindSpeed: { value: 1.3 },
      uWindFrequency: { value: 0.075 },
      uWindStrength: { value: 1.25 },
      uWindDirection: { value: new THREE.Vector2(0.85, 0.45).normalize() },
      uTrain1Pos: { value: new THREE.Vector3(0, 0, 0) },
      uTrain2Pos: { value: new THREE.Vector3(0, 0, 0) },
    };

    return { flowerGeo: instGeo, flowerUniforms: uniformsObj };
  }, []);

  // Update uniforms each frame
  useFrame((state, delta) => {
    if (uniforms) {
      uniforms.uTime.value += delta;
      uniforms.uTrain1Pos.value.copy(train1Pos);
      uniforms.uTrain2Pos.value.copy(train2Pos);
      uniforms.uMousePos.value.copy(mouseWorldPos);
      uniforms.uMouseActive.value = isMouseActive ? 1.0 : 0.0;
    }
    if (flowerUniforms) {
      flowerUniforms.uTime.value += delta;
      flowerUniforms.uTrain1Pos.value.copy(train1Pos);
      flowerUniforms.uTrain2Pos.value.copy(train2Pos);
    }
  });

  return (
    <group>
      {/* 1. Underlying Rolling Earth/Terrain Embankment */}
      <mesh position={[0, -0.45, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[115, 290, 48, 48]} />
        <meshStandardMaterial
          color="#16280E"
          roughness={0.95}
          metalness={0.05}
        />
      </mesh>

      {/* 2. Procedural Instanced Grass Field */}
      <mesh ref={meshRef} geometry={grassGeo} frustumCulled={false}>
        <shaderMaterial
          vertexShader={grassVertexShader}
          fragmentShader={grassFragmentShader}
          uniforms={uniforms}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* 3. Swaying Wildflowers & Meadow Heads */}
      <mesh ref={flowersMeshRef} geometry={flowerGeo} frustumCulled={false}>
        <shaderMaterial
          vertexShader={flowerVertexShader}
          fragmentShader={flowerFragmentShader}
          uniforms={flowerUniforms}
          side={THREE.DoubleSide}
          transparent={true}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}
