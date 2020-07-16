# Distcrs: A prototype decentralized CRS generation tool

This codebase contains a prototype implementation of a decentralized algorithm for generating Common Reference Strings for use in constructions such as Polynomial Commitments and ZK Snarks.  Currently, this codebase can generate CRSs for KZG polynomial commitments as well as the BabySNARK SNARK system, but it is written to be highly modular to accomidate many possible schemes.

Disclaimer: This is research code, please do not use it in production.


# Setup
To build, simply clone this repo and run `docker-compose build distcrs`
the image can be run with `docker-compose run --rm distcrs` and tests can be performed by navigating to `/src` and running `pytest test.py`. The only requirements for running this repo are a recent version of Python3 and the `py_ecc` and `pytest` pip packages, so this repo can be easily run outside of Docker.


# Code Overview
In Distcrs, we envision many players interacting with a decentralized append-only ledger (blockchain) in order to take turns adding randomness to a CRS. The blockchain serves as a publicly verifiable snapshot of all the CRS-generation work that has been done so far. In our construction, we divorce the notions of proofs of knowledge and proofs of integrity. What this means is that a player who adds new randomness to the CRS only needs to prove knowledge of an exponent that connects some portions of the old CRS with the new one. The structural correctness of the final CRS can be verified independently and only needs to be run on the end result, provided that all CRS updates were valid.

At the end of execution, a source of future randomness (random beacon) must be incorporated into the CRS so that an an adaptive adversary is unable to bias the end result. 
## The Player Class
A Player object represents a participant in the decentralized CRS generation protocol. It can send messages to other players and the blockchain, validate the existing CRS, and add its own randomness into the CRS (along with proofs of knowledge of the added randomness). Which actions a player performs are defined by the roles it is given. The roles are as follows (players can hold multiple roles)

- Roundstarter/Roundender: Players at the beginning or end of the round who need to perform tasks such as initializing the CRS or calling a random beacon
- Contributor: A player who adds its own randomness to the CRS and passes along the new CRS and knowledge proofs to the next player
- Checkpoint: A player who aggregates changes that have been made to the CRS and posts them to the blockchain
- Validator: A node that verifies the correctness of the entire blockchain (as well as any not-yet-published changes) before proceeding
## Decentralized Coordination
We envision the use of a blockchain as a means of decentralized coordination, however this codebase only simulates a blockchain with basic read and append functionality. All functions necessary to interact with the blockchain are passed into the Player objects, so these functions can easily be substituted with networked code that interacts with a testnet.

## Networking
For the purposes of this demo, networking is abstracted away and is simulated with Asyncio Queues (as all players are run on one thread). As with blockchain interaction, player to player interaction is simulated with send and receive functions that can easily be replaced with network code for distributed interaction. 