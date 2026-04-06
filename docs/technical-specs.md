# Noble Port Realty: Technical Specifications

## 1. Introduction

This document provides a detailed technical overview of the Noble Port Realty platform, a cutting-edge real estate investment solution that integrates real-world assets with blockchain technology. The platform is designed to provide a secure, transparent, and compliant environment for fractional ownership of premium real estate assets.

## 2. System Architecture

The Noble Port Realty platform is built on a modern, scalable, and secure architecture that leverages a combination of web technologies, backend services, and blockchain infrastructure. The following diagram illustrates the high-level system architecture:

![System Architecture Diagram](/home/ubuntu/system_architecture.png)

### 2.1. Frontend

*   **Framework:** React with Vite
*   **Description:** The frontend is a single-page application (SPA) that provides a responsive and user-friendly interface for investors. It allows users to browse properties, manage their portfolios, and interact with the platform's features.

### 2.2. Backend

*   **Language:** Python
*   **Framework:** API-first architecture (e.g., FastAPI, Django REST Framework)
*   **Description:** The backend provides a set of RESTful APIs that serve as the communication layer between the frontend and the underlying services. It handles business logic, data processing, and integration with external systems.

### 2.3. Database

*   **Primary Database:** PostgreSQL
*   **Secondary Database:** DocumentDB (or a similar NoSQL database)
*   **Description:** A combination of relational and NoSQL databases is used to store different types of data. PostgreSQL is used for structured data such as user information and transaction records, while a document database is used for less structured data like property details and media assets.

### 2.4. Blockchain Integration

*   **Blockchain:** Solana
*   **Token Standard:** Token 2022
*   **Description:** The platform integrates with the Solana blockchain to manage the tokenization of real estate assets. The Token 2022 standard is used to create and manage security tokens that represent ownership in the properties.

### 2.5. External Services

*   **KYC/AML:** Integration with a third-party provider for identity verification and anti-money laundering checks.
*   **Stablecoin:** Utilization of USDC for seamless and stable payment transactions.

## 3. Key Technical Features

### 3.1. Tokenization and Compliance

*   **Enforced Transfer Restrictions:** The Token 2022 standard allows for the implementation of transfer restrictions at the token level, ensuring that only KYC-verified users can hold and trade the tokens.
*   **Confidential Transfers:** Zero-knowledge proofs are used to enable private transactions, protecting the financial privacy of investors while maintaining auditability.
*   **Transfer Hooks:** Custom logic can be attached to token transfers to enforce specific rules, such as lock-up periods or investor accreditation checks.
*   **Investor Pass (SBT):** A non-transferable Soulbound Token (SBT) is issued to each verified investor, serving as a digital passport for accessing the platform's investment opportunities.

### 3.2. Multi-Chain Support

The platform supports nine different blockchains, providing investors with flexibility and choice. This is achieved through a blockchain abstraction layer that standardizes interactions with different networks.


### 3.3. Post-Quantum Signatures (ML-DSA)

The platform supports a post-quantum signature path based on ML-DSA (FIPS 204), with ML-DSA-65 as the primary deployment profile for balanced security and performance. During migration, hybrid verification policies can combine ECDSA and ML-DSA verification requirements.

See [ML-DSA Implementation Details](./ml-dsa-implementation.md) for parameter tables, implementation notes, and deployment guidance.
### 3.4. Security

Security is a top priority for the Noble Port Realty platform. The following measures are implemented to protect the system and its users:

*   **Smart Contract Audits:** All smart contracts undergo rigorous security audits by reputable third-party firms.
*   **Secure Coding Practices:** The development team follows best practices for secure coding to prevent common vulnerabilities.
*   **Infrastructure Security:** The platform's infrastructure is designed with security in mind, including firewalls, intrusion detection systems, and regular security assessments.

## 4. Conclusion

The technical architecture and features of the Noble Port Realty platform are designed to provide a robust, secure, and compliant solution for tokenized real estate investment. By combining the best of traditional finance and blockchain technology, the platform offers a unique and compelling value proposition to investors.

