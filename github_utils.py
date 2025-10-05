import os
import shutil
from git import Repo
from git.exc import GitCommandError

class GitHubUtils:
    def __init__(self, repos_dir="repos"):
        self.repos_dir = repos_dir
        os.makedirs(repos_dir, exist_ok=True)
    
    def clone_or_pull_repo(self, repo_url, repo_name, github_token=None):
        """Clone a repository or pull latest changes if it already exists"""
        local_path = os.path.join(self.repos_dir, repo_name)
        
        # Add token to URL if provided (for private repos)
        if github_token and 'github.com' in repo_url:
            if not repo_url.startswith('http'):
                repo_url = f'https://github.com/{repo_url}'
            repo_url = repo_url.replace('https://', f'https://{github_token}@')
        
        try:
            if os.path.exists(local_path):
                print(f"Pulling latest changes for {repo_name}...")
                repo = Repo(local_path)
                origin = repo.remotes.origin
                origin.pull()
                return local_path, repo
            else:
                print(f"Cloning repository {repo_name}...")
                repo = Repo.clone_from(repo_url, local_path)
                return local_path, repo
        except GitCommandError as e:
            raise Exception(f"Git operation failed: {str(e)}")
    
    def apply_fix_and_push(self, repo_path, file_path, fixed_code, github_token=None):
        """Apply fix to file, create branch, commit and push"""
        original_branch = None
        branch_name = "auto-fix-branch"
        
        try:
            repo = Repo(repo_path)
            
            # Determine and store the true default branch before any operations
            if repo.head.is_detached:
                # Detached HEAD - find default branch
                original_branch = self._get_default_branch(repo)
            else:
                # Store current branch, but validate it's not the auto-fix branch
                current = repo.active_branch.name
                if current == branch_name:
                    # We're on auto-fix branch from previous run - switch to default
                    original_branch = self._get_default_branch(repo)
                else:
                    original_branch = current
            
            # Final safety check - ensure original_branch is never the auto-fix branch
            if original_branch == branch_name:
                # This shouldn't happen, but if it does, force to a safe branch
                original_branch = None
                for safe_branch in ['main', 'master', 'develop']:
                    if safe_branch in repo.heads:
                        original_branch = safe_branch
                        break
                
                if not original_branch:
                    # Try to create main branch from current HEAD or remote
                    try:
                        if 'origin/main' in [ref.name for ref in repo.remotes.origin.refs]:
                            repo.git.checkout('-b', 'main', 'origin/main')
                        elif 'origin/master' in [ref.name for ref in repo.remotes.origin.refs]:
                            repo.git.checkout('-b', 'master', 'origin/master')
                        else:
                            repo.git.checkout('-b', 'main')
                        original_branch = repo.active_branch.name
                    except:
                        # Last resort - use any existing branch
                        if repo.heads:
                            original_branch = repo.heads[0].name
                        else:
                            raise Exception("No valid branch found and unable to create one")
            
            # Ensure we're on the original branch before any changes
            if repo.head.is_detached or repo.active_branch.name != original_branch:
                repo.git.checkout(original_branch)
            
            # Delete auto-fix branch if it exists (safe now since we're not on it)
            if branch_name in repo.heads:
                repo.delete_head(branch_name, force=True)
            
            # Create and checkout new branch
            repo.git.checkout('-b', branch_name)
            
            # Write fixed code to file
            full_file_path = os.path.join(repo_path, file_path)
            with open(full_file_path, 'w') as f:
                f.write(fixed_code)
            
            # Stage changes
            repo.index.add([file_path])
            
            # Commit changes
            repo.index.commit("🤖 Auto-fix applied by AI DevOps Assistant")
            
            # Push to remote with token in URL (ephemeral, not persisted)
            origin = repo.remotes.origin
            push_url = origin.url
            
            if github_token and 'github.com' in push_url:
                if '@' not in push_url:
                    push_url = push_url.replace('https://', f'https://{github_token}@')
                
                # Use ephemeral URL for push without persisting
                repo.git.push(push_url, branch_name, force=True)
            else:
                origin.push(branch_name, force=True)
            
            # Return to original branch
            repo.git.checkout(original_branch)
            
            return {
                'success': True,
                'branch': branch_name,
                'message': f'Fix pushed to branch {branch_name}'
            }
            
        except Exception as e:
            # Restore repo to safe state on any error
            try:
                repo = Repo(repo_path)
                
                # Determine safe branch to restore to
                restore_branch = None
                if original_branch and original_branch != branch_name:
                    restore_branch = original_branch
                else:
                    # Find a safe default branch
                    restore_branch = self._get_default_branch(repo)
                
                # Ensure restore branch exists before checkout
                if restore_branch and restore_branch not in repo.heads:
                    # Try to create from remote
                    try:
                        remote_ref = f'origin/{restore_branch}'
                        if remote_ref in [ref.name for ref in repo.remotes.origin.refs]:
                            repo.git.checkout('-b', restore_branch, remote_ref)
                        else:
                            repo.git.checkout('-b', restore_branch)
                    except:
                        # If creation fails, use any existing branch
                        if repo.heads:
                            for head in repo.heads:
                                if head.name != branch_name:
                                    restore_branch = head.name
                                    break
                
                # Perform checkout safely (handle detached HEAD)
                try:
                    if restore_branch:
                        repo.git.checkout(restore_branch)
                except:
                    # If checkout fails and we're detached, force checkout
                    if repo.heads:
                        for head in repo.heads:
                            if head.name != branch_name:
                                try:
                                    repo.git.checkout(head.name, force=True)
                                    break
                                except:
                                    continue
                
                # Reset any uncommitted changes
                try:
                    repo.git.reset('--hard')
                except:
                    pass
                
                # Clean up auto-fix branch if it was created and we're not on it
                try:
                    if branch_name in repo.heads:
                        current = repo.active_branch.name if not repo.head.is_detached else None
                        if current != branch_name:
                            repo.delete_head(branch_name, force=True)
                except:
                    pass
                    
            except Exception as cleanup_error:
                # Log cleanup failure but don't mask original error
                print(f"Cleanup failed: {cleanup_error}")
                
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_default_branch(self, repo):
        """Find the default branch (main or master), avoiding auto-fix branch"""
        auto_fix_branch = "auto-fix-branch"
        
        # Try to get remote HEAD (most reliable way to find default branch)
        try:
            if repo.remotes.origin.refs:
                remote_head = repo.remotes.origin.refs.HEAD
                if remote_head.reference:
                    branch_name = remote_head.reference.name.split('/')[-1]
                    if branch_name != auto_fix_branch and branch_name in repo.heads:
                        return branch_name
        except:
            pass
        
        # Try common default branches
        for branch in ['main', 'master', 'develop', 'dev']:
            if branch in repo.heads and branch != auto_fix_branch:
                return branch
        
        # Find first non-auto-fix branch
        if repo.heads:
            for head in repo.heads:
                if head.name != auto_fix_branch:
                    return head.name
        
        # Last resort - return main (will be created if needed)
        return 'main'
    
    def get_file_content(self, repo_path, file_path):
        """Read file content from repository"""
        full_path = os.path.join(repo_path, file_path)
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                return f.read()
        return None
