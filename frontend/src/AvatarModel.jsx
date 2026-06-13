import React, { useEffect, useRef, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { FBXLoader } from 'three/examples/jsm/loaders/FBXLoader.js'
import { VRMLoaderPlugin } from '@pixiv/three-vrm'

// ===== BONE MAP =====
const mixamoVRMRigMap = {
    mixamorigHips: 'hips', mixamorigSpine: 'spine',
    mixamorigSpine1: 'chest', mixamorigSpine2: 'upperChest',
    mixamorigNeck: 'neck', mixamorigHead: 'head',
    mixamorigLeftShoulder: 'leftShoulder', mixamorigLeftArm: 'leftUpperArm',
    mixamorigLeftForeArm: 'leftLowerArm', mixamorigLeftHand: 'leftHand',
    mixamorigRightShoulder: 'rightShoulder', mixamorigRightArm: 'rightUpperArm',
    mixamorigRightForeArm: 'rightLowerArm', mixamorigRightHand: 'rightHand',
    mixamorigLeftUpLeg: 'leftUpperLeg', mixamorigLeftLeg: 'leftLowerLeg',
    mixamorigLeftFoot: 'leftFoot', mixamorigRightUpLeg: 'rightUpperLeg',
    mixamorigRightLeg: 'rightLowerLeg', mixamorigRightFoot: 'rightFoot',
};

// ===== RETARGET FUNCTION =====
function loadMixamoAnimation(url, vrm) {
    const loader = new FBXLoader();
    return loader.loadAsync(url).then((asset) => {
        const clip = THREE.AnimationClip.findByName(asset.animations, 'mixamo.com');
        const tracks = [];
        const restRotationInverse = new THREE.Quaternion();
        const parentRestWorldRotation = new THREE.Quaternion();
        const _quatA = new THREE.Quaternion();
        const _vec3 = new THREE.Vector3();

        const motionHipsHeight = asset.getObjectByName('mixamorigHips').position.y;
        const vrmHipsY = vrm.humanoid?.getNormalizedBoneNode('hips').getWorldPosition(_vec3).y;
        const vrmRootY = vrm.scene.getWorldPosition(_vec3).y;
        const vrmHipsHeight = Math.abs(vrmHipsY - vrmRootY);
        const hipsPositionScale = vrmHipsHeight / motionHipsHeight;

        clip.tracks.forEach((track) => {
            const trackSplitted = track.name.split('.');
            const mixamoRigName = trackSplitted[0];
            const vrmBoneName = mixamoVRMRigMap[mixamoRigName];
            if (!vrmBoneName) return; // skip if not in map

            const vrmNode = vrm.humanoid?.getNormalizedBoneNode(vrmBoneName);
            const vrmNodeName = vrmNode?.name;
            const mixamoRigNode = asset.getObjectByName(mixamoRigName);

            if (vrmNodeName && mixamoRigNode) {
                const propertyName = trackSplitted[1];
                mixamoRigNode.getWorldQuaternion(restRotationInverse).invert();
                mixamoRigNode.parent.getWorldQuaternion(parentRestWorldRotation);

                if (track instanceof THREE.QuaternionKeyframeTrack) {
                    for (let i = 0; i < track.values.length; i += 4) {
                        const flatQuat = track.values.slice(i, i + 4);
                        _quatA.fromArray(flatQuat);
                        _quatA.premultiply(parentRestWorldRotation).multiply(restRotationInverse);
                        _quatA.toArray(flatQuat);
                        flatQuat.forEach((v, index) => { track.values[index + i] = v; });
                    }
                    tracks.push(new THREE.QuaternionKeyframeTrack(
                        `${vrmNodeName}.${propertyName}`, track.times,
                        track.values.map((v, i) => (vrm.meta?.metaVersion === '0' && i % 2 === 0 ? -v : v))
                    ));
                } else if (track instanceof THREE.VectorKeyframeTrack) {
                    let value = track.values.map((v, i) =>
                        (vrm.meta?.metaVersion === '0' && i % 3 !== 1 ? -v : v) * hipsPositionScale
                    );
                    if (vrmBoneName === 'hips' && propertyName === 'position') {
                        for (let i = 0; i < value.length; i += 3) {
                            value[i] = 0;     // Lock X translation
                            value[i + 2] = 0; // Lock Z translation
                        }
                    }
                    tracks.push(new THREE.VectorKeyframeTrack(
                        `${vrmNodeName}.${propertyName}`, track.times, value
                    ));
                }
            }
        });
        return new THREE.AnimationClip(url, clip.duration, tracks);
    });
}

export default function AvatarModel({
    scale = 1,
    position = [0, 0, 0],
    mini = false,
    showWaistUp = false,
    modelId = 'female',
    quality = 'high'
}) {
    const [vrm, setVrm] = useState(null)
    const mixerRef = useRef(null)
    const actionsRef = useRef({})
    const currentActionRef = useRef(null)
    const emotionRef = useRef('neutral')

    // Adjust position to show from waist up
    const adjustedPosition = showWaistUp
        ? [position[0], position[1], position[2]]
        : position

    useEffect(() => {
        setVrm(null) // clear previous model

        const loader = new GLTFLoader()
        loader.register((parser) => new VRMLoaderPlugin(parser))

        // Load different VRM files based on quality setting
        // Users should provide: male_low.vrm, male_med.vrm, malecharacter.vrm (high)
        //                       female_low.vrm, female_med.vrm, AvatarSample_I.vrm (high)
        const modelPaths = {
            male: { low: '/male_low.vrm', medium: '/male_med.vrm', high: '/malecharacter.vrm' },
            female: { low: '/female_low.vrm', medium: '/female_med.vrm', high: '/AvatarSample_I.vrm' },
        }
        const modelUrl = (modelPaths[modelId] || modelPaths.female)[quality] || modelPaths[modelId].high

        loader.load(modelUrl, (gltf) => {
            const vrmInstance = gltf.userData.vrm
            vrmInstance.scene.traverse((obj) => { if (obj.isMesh) obj.frustumCulled = false })

            const mixer = new THREE.AnimationMixer(vrmInstance.scene)
            mixerRef.current = mixer

            Promise.all([
                loadMixamoAnimation(modelId === 'male' ? '/Standard Idle.fbx' : '/Idle (3).fbx', vrmInstance),
                loadMixamoAnimation('/Talking (1).fbx', vrmInstance),
                loadMixamoAnimation('/Hip Hop Dancing.fbx', vrmInstance),
                loadMixamoAnimation('/Jumping Jacks.fbx', vrmInstance),
                loadMixamoAnimation('/Victory.fbx', vrmInstance)
            ]).then(([idleClip, talkClip, danceClip, jumpingJacksClip, victoryClip]) => {
                actionsRef.current['idle'] = mixer.clipAction(idleClip)
                actionsRef.current['talking'] = mixer.clipAction(talkClip)
                actionsRef.current['dance'] = mixer.clipAction(danceClip)
                actionsRef.current['jumping_jacks'] = mixer.clipAction(jumpingJacksClip)
                actionsRef.current['victory'] = mixer.clipAction(victoryClip)

                const idleAction = actionsRef.current['idle']
                if (idleAction) {
                    idleAction.play()
                    currentActionRef.current = idleAction
                }
                setVrm(vrmInstance)
            }).catch(err => {
                console.error('[VRM] Animation retargeting error:', err)
                // Still set VRM so it renders even if animations fail
                setVrm(vrmInstance)
            })
        }, undefined, (err) => {
            console.error('[VRM] Load error:', err)
        })

        return () => {
            if (vrm) {
                // dispose vrm?
            }
        }
    }, [modelId, quality]) // Reload when modelId or quality changes

    const playAnimation = (name) => {
        const next = actionsRef.current[name]
        const current = currentActionRef.current

        if (next && current && next !== current) {
            next.reset().play()
            next.crossFadeFrom(current, 0.3, true)
            currentActionRef.current = next
        } else if (next && !current) {
            next.play()
            currentActionRef.current = next
        }
    }

    // 1. TALKING (Looping)
    useEffect(() => {
        const onTalking = (e) => {
            const isTalking = e.detail
            if (isTalking) {
                playAnimation('talking')
            } else {
                playAnimation('idle')
            }
        }
        window.addEventListener('aura:talking', onTalking)
        return () => window.removeEventListener('aura:talking', onTalking)
    }, [vrm])

    // 1.5. ACTIONS (Dance, Jumping Jacks, Victory, etc)
    useEffect(() => {
        const onAction = (e) => {
            const action = e.detail
            const durations = { dance: 8000, jumping_jacks: 6000, victory: 5000 }
            if (actionsRef.current[action]) {
                playAnimation(action)
                setTimeout(() => {
                    playAnimation('idle')
                }, durations[action] || 6000)
            }
        }
        window.addEventListener('aura:setAction', onAction)
        return () => window.removeEventListener('aura:setAction', onAction)
    }, [vrm])

    // 2. EMOTIONS (One Shot triggers)
    useEffect(() => {
        const onEmotion = (e) => {
            if (!vrm) return
            const emo = e.detail || 'neutral'
            let vrmEmo = 'neutral'
            if (['happy', 'thankful', 'laugh'].includes(emo)) vrmEmo = 'happy'
            if (['sad', 'bashful'].includes(emo)) vrmEmo = 'sad'
            if (['shock', 'surprised'].includes(emo)) vrmEmo = 'surprised'
            if (emo === 'angry') vrmEmo = 'angry'

            emotionRef.current = vrmEmo

            const allExprs = ['happy', 'sad', 'angry', 'surprised', 'neutral']
            allExprs.forEach(expr => {
                vrm.expressionManager.setValue(expr, 0)
            })
            if (vrmEmo !== 'neutral') {
                vrm.expressionManager.setValue(vrmEmo, 1.0)
                setTimeout(() => {
                    if (vrm) {
                        vrm.expressionManager.setValue(vrmEmo, 0)
                        emotionRef.current = 'neutral'
                    }
                }, 3000)
            }
        }
        window.addEventListener('aura:setEmotion', onEmotion)
        return () => window.removeEventListener('aura:setEmotion', onEmotion)
    }, [vrm])

    // Listen for events to control morphs (lip-sync)
    useEffect(() => {
        function onSetMorph(e) {
            if (!vrm) return
            const { name, value } = e?.detail || {}
            if (typeof value !== 'number') return

            if (name === 'mouthOpen') {
                vrm.expressionManager.setValue('aa', value)
            }
        }
        window.addEventListener('aura:setMorph', onSetMorph)
        return () => window.removeEventListener('aura:setMorph', onSetMorph)
    }, [vrm])

    const blinkTimerRef = useRef(0)
    const idleTimeRef = useRef(0)

    // Animation Loop
    useFrame((state, delta) => {
        if (vrm) {
            vrm.update(delta)
        }
        if (mixerRef.current) mixerRef.current.update(delta)

        blinkTimerRef.current += delta
        idleTimeRef.current += delta

        // Breathing
        if (vrm) {
            const breathe = 1 + Math.sin(idleTimeRef.current * 1.5) * 0.008
            vrm.scene.scale.setScalar(scale * breathe)
        }

        // Blinking
        if (blinkTimerRef.current > 4 + Math.random() * 4) {
            blinkTimerRef.current = 0
            if (vrm) {
                vrm.expressionManager.setValue('blink', 1.0)
                setTimeout(() => {
                    if (vrm) vrm.expressionManager.setValue('blink', 0.0)
                }, 150)
            }
        }

        // Eye Tracking
        if (vrm && !mini && vrm.lookAt) {
            vrm.lookAt.target = state.camera
        }
    })

    if (!vrm) return null

    return <primitive object={vrm.scene} scale={scale} position={adjustedPosition} rotation={[0, Math.PI, 0]} />
}
