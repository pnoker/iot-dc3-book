# How to Read This Book

If "AI agents" is what drew you to this book, let me first ask you not to start with AI.

In a real system, what an agent can read depends on whether devices are already connected and whether the data is continuous and trustworthy; what it can do depends on which tools the platform has opened up, and what permissions and constraints it sets. Without these foundations, any discussion of intelligence is likely to remain at the demo stage.

So this book begins with industrial software and IoT platforms. Part I first looks at how devices, networks, and data form a complete end-to-end chain, and explains what boundaries traditional industrial software left behind. In Part II we discuss how a cloud-native architecture carries a growing population of devices and services, and how AI agents take part in this system within security boundaries. Part III brings all of it back to industry, cities, agriculture, and other scenarios, and closes with IoT DC3 — tracing one platform's step-by-step path from protocol access to agent applications.

You don't need to memorize every protocol and framework on a first read. What deserves attention is what problem each layer solves, what it depends on, and what capability it hands to the layer above. Hold on to that thread, and even as specific technologies change, you will still know where to begin in understanding an IoT system.

As for prerequisites: you don't need IoT project experience, nor do you need to be familiar with any particular protocol or framework in advance — a basic grounding in programming and computer networks is enough to read the whole book comfortably.

## Suggested Paths

The book follows one continuous technical path, but not every reader needs to read it from the first page to the last.

- If you are new to IoT, start at Chapter 1 and read straight through. The first five chapters give you a complete picture of how devices, networks, the platform, and data fit together.
- If you already work on device access or platform development, skim Part I and spend more time on Chapters 5–9, focusing on how the platform, cloud-native architecture, agents, and security connect.
- If you are familiar with AI application development but new to industrial environments, read at least Chapters 2, 4, and 5 before moving on to Chapter 7. It will be much easier to understand where the data and capabilities come from before a model calls a tool.
- If you want to go straight to IoT DC3, start with Chapter 14. But be aware that this chapter is where the book's concepts converge: the mechanics of the message bus and time-series storage are developed in Chapter 5, the Agent Runtime in Chapter 7, and the security baseline in Chapter 8. If you meet an unfamiliar concept while skimming, just follow the back-references within Chapter 14 to the relevant chapter — there is no need to interrupt your progress and read forward from the beginning.

Running the system in this book yourself takes only modest preparation: a development machine with Docker (or Podman) and Compose installed, JDK 21, and an MQTT client (such as mosquitto_pub) for simulating devices reporting data. The hands-on part of Chapter 14 provides a 10-step smoke-test command sequence you can copy directly, along with a troubleshooting table; executed in order, they verify the complete chain from device access and data storage to agent invocation.

The code, figures, and case studies in this book exist to illustrate mechanisms and trade-offs. As you read, keep asking: which layer this technology actually solves a problem for, and do the conditions it relies on hold in your own scenario?
