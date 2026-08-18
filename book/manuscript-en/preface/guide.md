# How to Read This Book

If you picked up this book because of the words "AI agents," let me first ask you not to start with the AI.

In a real system, what an agent can read depends on whether devices are already connected and whether the data is continuous and trustworthy; what it can do depends on which tools the platform has opened up, and under what permissions and constraints. Away from these foundations, any discussion of intelligence tends to stay in the demo.

So this book starts from industrial software and the IoT platform. Part I first looks at how devices, networks, and data form one complete chain, and explains what boundaries traditional industrial software left behind. In Part II we discuss how a cloud-native architecture carries a growing population of devices and services, and how AI agents take part in this system within security boundaries. Part III brings all of it back to industry, cities, agriculture, and other scenarios, and closes with IoT DC3 — watching one platform walk, step by step, from protocol access to agent applications.

You don't need to memorize every protocol and framework on a first read. What deserves attention is what problem each layer solves, what it depends on, and what capability it hands to the layer above. Hold on to that thread, and even as specific technologies change, you will still know where to start when understanding an IoT system.

## Suggested Paths

The book follows one continuous technical path, but not every reader needs to read it from the first page to the last.

- If you are new to IoT, read from Chapter 1 in order. The first five chapters will build the complete relationship between devices, networks, the platform, and data.
- If you already work on device access or platform development, skim Part I and spend more time on Chapters 5–9, focusing on how the platform, cloud-native architecture, agents, and security connect.
- If you are familiar with AI application development but not with the industrial field, read at least Chapters 2, 4, and 5 before entering Chapter 7. It will be much easier to understand where the data and capabilities come from before a model calls a tool.
- If you want to go straight to IoT DC3, start with Chapter 14, then return to earlier chapters as problems arise.

The code, figures, and project cases in this book exist to illustrate mechanisms and trade-offs. As you read, keep asking: which layer's problem does this technology actually solve, and do the conditions it relies on hold in your own scenario?
