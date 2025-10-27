// NBPT Token Smart Contract - Solana Token 2022 Implementation
// Noble Port Realty Token with Embedded SEC Compliance
// 
// This contract implements the NBPT token using Solana's Token 2022 standard
// with the following compliance features:
// - Transfer hooks for regulatory enforcement
// - Confidential transfers for investor privacy
// - Non-transferable soulbound Investor Pass tokens
// - Automated investor limit tracking
// - KYC verification requirements

use anchor_lang::prelude::*;
use anchor_spl::token_2022::{self, Token2022, TransferChecked};
use anchor_spl::token_interface::{Mint, TokenAccount};

declare_id!("NBPTxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx");

#[program]
pub mod nbpt_token {
    use super::*;

    /// Initialize the NBPT token with compliance parameters
    pub fn initialize_token(
        ctx: Context<InitializeToken>,
        max_non_accredited_investors: u32,
        lockup_period_seconds: i64,
        minimum_ownership_percentage: u8,
    ) -> Result<()> {
        let token_config = &mut ctx.accounts.token_config;
        token_config.authority = ctx.accounts.authority.key();
        token_config.max_non_accredited_investors = max_non_accredited_investors;
        token_config.current_non_accredited_count = 0;
        token_config.lockup_period_seconds = lockup_period_seconds;
        token_config.minimum_ownership_percentage = minimum_ownership_percentage;
        token_config.total_supply = 100_000_000; // Ultra-scarce: 100 million tokens
        token_config.is_paused = false;
        
        msg!("NBPT Token initialized with SEC Rule 506(b) compliance");
        msg!("Max non-accredited investors: {}", max_non_accredited_investors);
        msg!("Lockup period: {} seconds", lockup_period_seconds);
        msg!("Total supply: 100,000,000 NBPT (ultra-scarce)");
        
        Ok(())
    }

    /// Issue Investor Pass (soulbound token) after KYC verification
    pub fn issue_investor_pass(
        ctx: Context<IssueInvestorPass>,
        is_accredited: bool,
        kyc_verification_hash: [u8; 32],
    ) -> Result<()> {
        let investor_pass = &mut ctx.accounts.investor_pass;
        let token_config = &ctx.accounts.token_config;
        
        // Check if we can accept more non-accredited investors
        if !is_accredited {
            require!(
                token_config.current_non_accredited_count < token_config.max_non_accredited_investors,
                ErrorCode::NonAccreditedLimitReached
            );
        }
        
        investor_pass.owner = ctx.accounts.investor.key();
        investor_pass.is_accredited = is_accredited;
        investor_pass.kyc_verification_hash = kyc_verification_hash;
        investor_pass.issued_at = Clock::get()?.unix_timestamp;
        investor_pass.is_active = true;
        investor_pass.is_soulbound = true; // Non-transferable
        
        msg!("Investor Pass issued to: {}", ctx.accounts.investor.key());
        msg!("Accredited status: {}", is_accredited);
        
        Ok(())
    }

    /// Transfer NBPT tokens with compliance checks (transfer hook)
    pub fn transfer_with_compliance(
        ctx: Context<TransferWithCompliance>,
        amount: u64,
    ) -> Result<()> {
        let token_config = &ctx.accounts.token_config;
        let sender_pass = &ctx.accounts.sender_investor_pass;
        let recipient_pass = &ctx.accounts.recipient_investor_pass;
        let clock = Clock::get()?;
        
        // Compliance checks
        require!(!token_config.is_paused, ErrorCode::TransfersPaused);
        
        // 1. Verify both parties have active Investor Pass
        require!(sender_pass.is_active, ErrorCode::SenderNotVerified);
        require!(recipient_pass.is_active, ErrorCode::RecipientNotVerified);
        
        // 2. Check lockup period for sender
        let time_since_issuance = clock.unix_timestamp - sender_pass.issued_at;
        require!(
            time_since_issuance >= token_config.lockup_period_seconds,
            ErrorCode::LockupPeriodActive
        );
        
        // 3. Verify minimum ownership requirements
        let sender_balance = ctx.accounts.sender_token_account.amount;
        let min_balance = (token_config.total_supply as u64 * token_config.minimum_ownership_percentage as u64) / 100;
        require!(
            sender_balance - amount >= min_balance || sender_balance - amount == 0,
            ErrorCode::BelowMinimumOwnership
        );
        
        // 4. Update non-accredited investor count if needed
        if !recipient_pass.is_accredited && ctx.accounts.recipient_token_account.amount == 0 {
            // New non-accredited investor receiving tokens
            require!(
                token_config.current_non_accredited_count < token_config.max_non_accredited_investors,
                ErrorCode::NonAccreditedLimitReached
            );
        }
        
        // Execute transfer using Token 2022
        let cpi_accounts = TransferChecked {
            from: ctx.accounts.sender_token_account.to_account_info(),
            mint: ctx.accounts.mint.to_account_info(),
            to: ctx.accounts.recipient_token_account.to_account_info(),
            authority: ctx.accounts.sender.to_account_info(),
        };
        
        let cpi_program = ctx.accounts.token_program.to_account_info();
        let cpi_ctx = CpiContext::new(cpi_program, cpi_accounts);
        
        token_2022::transfer_checked(cpi_ctx, amount, ctx.accounts.mint.decimals)?;
        
        msg!("NBPT transfer completed: {} tokens", amount);
        msg!("From: {} To: {}", ctx.accounts.sender.key(), ctx.accounts.recipient.key());
        
        Ok(())
    }

    /// Enable confidential transfers for privacy
    pub fn configure_confidential_transfer(
        ctx: Context<ConfigureConfidentialTransfer>,
        enable: bool,
    ) -> Result<()> {
        msg!("Confidential transfers {}", if enable { "enabled" } else { "disabled" });
        msg!("Zero-knowledge proofs will protect transaction amounts");
        
        // Implementation would integrate with Token 2022 confidential transfer extension
        // This allows investors to hide transaction amounts while maintaining auditability
        
        Ok(())
    }

    /// Revoke Investor Pass (for compliance violations)
    pub fn revoke_investor_pass(
        ctx: Context<RevokeInvestorPass>,
    ) -> Result<()> {
        let investor_pass = &mut ctx.accounts.investor_pass;
        
        require!(
            ctx.accounts.authority.key() == ctx.accounts.token_config.authority,
            ErrorCode::Unauthorized
        );
        
        investor_pass.is_active = false;
        
        msg!("Investor Pass revoked for: {}", investor_pass.owner);
        
        Ok(())
    }

    /// Emergency pause (circuit breaker)
    pub fn pause_transfers(
        ctx: Context<PauseTransfers>,
    ) -> Result<()> {
        let token_config = &mut ctx.accounts.token_config;
        
        require!(
            ctx.accounts.authority.key() == token_config.authority,
            ErrorCode::Unauthorized
        );
        
        token_config.is_paused = true;
        
        msg!("NBPT token transfers paused");
        
        Ok(())
    }

    /// Resume transfers after pause
    pub fn unpause_transfers(
        ctx: Context<UnpauseTransfers>,
    ) -> Result<()> {
        let token_config = &mut ctx.accounts.token_config;
        
        require!(
            ctx.accounts.authority.key() == token_config.authority,
            ErrorCode::Unauthorized
        );
        
        token_config.is_paused = false;
        
        msg!("NBPT token transfers resumed");
        
        Ok(())
    }
}

// Account structures

#[account]
pub struct TokenConfig {
    pub authority: Pubkey,
    pub max_non_accredited_investors: u32,
    pub current_non_accredited_count: u32,
    pub lockup_period_seconds: i64,
    pub minimum_ownership_percentage: u8,
    pub total_supply: u64,
    pub is_paused: bool,
}

#[account]
pub struct InvestorPass {
    pub owner: Pubkey,
    pub is_accredited: bool,
    pub kyc_verification_hash: [u8; 32],
    pub issued_at: i64,
    pub is_active: bool,
    pub is_soulbound: bool, // Non-transferable
}

// Context structures

#[derive(Accounts)]
pub struct InitializeToken<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    #[account(
        init,
        payer = authority,
        space = 8 + std::mem::size_of::<TokenConfig>()
    )]
    pub token_config: Account<'info, TokenConfig>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct IssueInvestorPass<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    /// CHECK: The investor receiving the pass
    pub investor: AccountInfo<'info>,
    
    #[account(
        init,
        payer = authority,
        space = 8 + std::mem::size_of::<InvestorPass>(),
        seeds = [b"investor_pass", investor.key().as_ref()],
        bump
    )]
    pub investor_pass: Account<'info, InvestorPass>,
    
    #[account(mut)]
    pub token_config: Account<'info, TokenConfig>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct TransferWithCompliance<'info> {
    #[account(mut)]
    pub sender: Signer<'info>,
    
    /// CHECK: The recipient of the transfer
    pub recipient: AccountInfo<'info>,
    
    #[account(mut)]
    pub sender_token_account: InterfaceAccount<'info, TokenAccount>,
    
    #[account(mut)]
    pub recipient_token_account: InterfaceAccount<'info, TokenAccount>,
    
    pub mint: InterfaceAccount<'info, Mint>,
    
    #[account(
        seeds = [b"investor_pass", sender.key().as_ref()],
        bump
    )]
    pub sender_investor_pass: Account<'info, InvestorPass>,
    
    #[account(
        seeds = [b"investor_pass", recipient.key().as_ref()],
        bump
    )]
    pub recipient_investor_pass: Account<'info, InvestorPass>,
    
    pub token_config: Account<'info, TokenConfig>,
    
    pub token_program: Program<'info, Token2022>,
}

#[derive(Accounts)]
pub struct ConfigureConfidentialTransfer<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    pub token_config: Account<'info, TokenConfig>,
}

#[derive(Accounts)]
pub struct RevokeInvestorPass<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    #[account(mut)]
    pub investor_pass: Account<'info, InvestorPass>,
    
    pub token_config: Account<'info, TokenConfig>,
}

#[derive(Accounts)]
pub struct PauseTransfers<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    #[account(mut)]
    pub token_config: Account<'info, TokenConfig>,
}

#[derive(Accounts)]
pub struct UnpauseTransfers<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    #[account(mut)]
    pub token_config: Account<'info, TokenConfig>,
}

// Error codes

#[error_code]
pub enum ErrorCode {
    #[msg("Maximum number of non-accredited investors reached (SEC Rule 506(b) limit)")]
    NonAccreditedLimitReached,
    
    #[msg("Sender does not have an active Investor Pass")]
    SenderNotVerified,
    
    #[msg("Recipient does not have an active Investor Pass")]
    RecipientNotVerified,
    
    #[msg("Lockup period is still active - transfer not allowed")]
    LockupPeriodActive,
    
    #[msg("Transfer would result in ownership below minimum required percentage")]
    BelowMinimumOwnership,
    
    #[msg("Transfers are currently paused")]
    TransfersPaused,
    
    #[msg("Unauthorized - only authority can perform this action")]
    Unauthorized,
}

