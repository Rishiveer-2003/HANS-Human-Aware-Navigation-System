"""
================================================================================
PPO Training Script for HANS Navigation Policy
================================================================================

This script is the entry point for training a PPO (Proximal Policy Optimization)
agent in the HANSNavEnv environment.

ARCHITECTURE:
  - Policy Network: MLP (3-layer fully connected)
  - Algorithm: PPO (clip-based policy gradient)
  - Framework: Stable Baselines3
  - Training: 100,000 timesteps (configurable)
  - Checkpoints: Saved every 20,000 timesteps for inspection

USAGE:
  Training:
    python hans_rl/train.py --timesteps 100000 --model models/hans_ppo.zip
  
  Evaluation (use saved model):
    python hans_rl/train.py --eval --model models/hans_ppo.zip --episodes 10
  
  Evaluation with different checkpoint:
    python hans_rl/train.py --eval --model models/hans_ppo_20000_steps.zip --episodes 5

OUTPUT:
  - models/hans_ppo.zip: Final trained model
  - models/hans_ppo_<N>_steps.zip: Checkpoints every N steps
================================================================================
"""

import argparse
import os
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from hans_rl.envs import HANSNavEnv


def train(total_timesteps: int = 100000, save_path: str = "models/hans_ppo.zip"):
    """
    Train a PPO agent in the HANS navigation environment.
    
    Training hyperparameters (stable-baselines3 defaults):
      - Policy: MlpPolicy (3-layer MLP: [64, 64] hidden units)
      - Learning rate: 3e-4 (Adam optimizer)
      - Entropy coefficient: 0.0 (from env)
      - Clip range: 0.2 (PPO epsilon)
      - GAE lambda: 0.95
      - N epochs: 10 (per PPO update)
      - Batch size: 64
    
    Args:
        total_timesteps: Total environment steps to train (int)
        save_path: Path to save final trained model (str)
    
    Example:
        train(total_timesteps=50000, save_path="models/test.zip")
    """
    # Create models directory if it doesn't exist
    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    
    print("[TRAINING] Initializing HANSNavEnv...")
    env = HANSNavEnv()
    
    print("[TRAINING] Setting up checkpoint callback...")
    # Save checkpoint every 20k steps for inspection and resuming
    checkpoint_callback = CheckpointCallback(
        save_freq=20000,
        save_path="models/",
        name_prefix="hans_ppo",
        verbose=1
    )
    
    print("[TRAINING] Initializing PPO model with MlpPolicy...")
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
    )
    
    print(f"[TRAINING] Starting training for {total_timesteps} timesteps...")
    print(f"[TRAINING] Using callbacks: CheckpointCallback (every 20k steps)")
    model.learn(
        total_timesteps=total_timesteps,
        callback=checkpoint_callback,
        progress_bar=True
    )
    
    print(f"[TRAINING] Saving final model to {save_path}...")
    model.save(save_path)
    print(f"[TRAINING] SUCCESS: Trained model saved to {save_path}")
    
    env.close()


def evaluate(model_path: str = "models/hans_ppo.zip", episodes: int = 5):
    """
    Evaluate a trained PPO model on the HANS environment.
    
    Evaluation uses deterministic (greedy) policy without exploration noise.
    Episodes terminate on success (reached goal) or failure (collision/timeout).
    
    Args:
        model_path: Path to saved model .zip file (str)
        episodes: Number of evaluation episodes to run (int)
    
    Example:
        evaluate(model_path="models/hans_ppo.zip", episodes=10)
    
    Returns:
        None (prints results to stdout)
    """
    print(f"[EVALUATION] Loading model from {model_path}...")
    env = HANSNavEnv()
    model = PPO.load(model_path, env=env)
    
    print(f"[EVALUATION] Running {episodes} evaluation episodes...")
    print(f"{'Episode':<10} {'Reward':<10} {'Steps':<10} {'Success':<10}")
    print("-" * 40)
    
    rewards = []
    successes = 0
    step_counts = []
    
    for ep in range(episodes):
        obs, _ = env.reset()
        done = False
        total_reward = 0.0
        
        # Rollout episode with deterministic policy (no exploration)
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, _, info = env.step(action)
            total_reward += reward
        
        # Check if episode was successful (reached goal)
        success = info["distance_to_goal"] < 0.5
        if success:
            successes += 1
        
        rewards.append(total_reward)
        step_counts.append(info['steps'])
        print(
            f"Episode {ep + 1:<8} {total_reward:>9.2f} {info['steps']:<10} "
            f"{'✓ Goal' if success else 'Timeout':<10}"
        )
    
    print("-" * 40)
    print(f"{'Summary':<10}")
    print(f"  Average reward: {np.mean(rewards):.2f} ± {np.std(rewards):.2f}")
    print(f"  Success rate:   {successes}/{episodes} ({100*successes/episodes:.1f}%)")
    print(f"  Avg steps:      {np.mean(step_counts):.1f} ± {np.std(step_counts):.1f}")
    
    env.close()


if __name__ == "__main__":
    """
    Command-line interface for training and evaluating the HANS policy.
    
    Arguments:
      --timesteps: Total training timesteps (default 100000)
      --model: Path to save/load model (default models/hans_ppo.zip)
      --eval: Flag to run evaluation instead of training
      --episodes: Number of evaluation episodes (default 5)
    
    Examples:
      # Train for 100k steps
      $ python hans_rl/train.py
      
      # Train for 50k steps with custom output
      $ python hans_rl/train.py --timesteps 50000 --model my_model.zip
      
      # Evaluate saved model
      $ python hans_rl/train.py --eval --model models/hans_ppo.zip --episodes 10
      
      # Evaluate checkpoint from training
      $ python hans_rl/train.py --eval --model models/hans_ppo_20000_steps.zip --episodes 5
    """
    parser = argparse.ArgumentParser(
        description="Train or evaluate HANS PPO navigation policy.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train for 100k steps (default)
  python hans_rl/train.py
  
  # Train for 50k steps
  python hans_rl/train.py --timesteps 50000
  
  # Evaluate a trained model
  python hans_rl/train.py --eval --episodes 10
  
  # Evaluate a specific checkpoint
  python hans_rl/train.py --eval --model models/hans_ppo_40000_steps.zip
        """
    )
    parser.add_argument(
        "--timesteps",
        type=int,
        default=100000,
        help="Total training timesteps (default: 100000)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="models/hans_ppo.zip",
        help="Path to save/load model (default: models/hans_ppo.zip)"
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Run evaluation of saved model instead of training"
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=5,
        help="Number of evaluation episodes (default: 5)"
    )
    
    args = parser.parse_args()

    if args.eval:
        print(f"\n{'='*60}")
        print(f"EVALUATION MODE")
        print(f"{'='*60}")
        evaluate(model_path=args.model, episodes=args.episodes)
    else:
        print(f"\n{'='*60}")
        print(f"TRAINING MODE")
        print(f"{'='*60}")
        train(total_timesteps=args.timesteps, save_path=args.model)
