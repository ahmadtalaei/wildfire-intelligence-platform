/**
 * WebGL Wind Particle System
 * Based on techniques used by Windy.com and earth.nullschool.net
 * Renders millions of particles showing wind flow patterns
 */

import { WeatherLayerData, WindGridPoint } from '../../services/AdvancedWeatherService';

export interface ParticleSystemOptions {
  numParticles: number;
  particleSpeed: number;
  particleLifetime: number;
  fadeOpacity: number;
  dropRate: number;
  dropRateBump: number;
  speedFactor: number;
  colors: {
    slow: [number, number, number];
    medium: [number, number, number];
    fast: [number, number, number];
  };
}

export class WindParticleSystem {
  private canvas: HTMLCanvasElement;
  private gl: WebGLRenderingContext;
  private weatherData: WeatherLayerData | null = null;

  // WebGL resources
  private windTexture: WebGLTexture | null = null;
  private particleStateTexture0: WebGLTexture | null = null;
  private particleStateTexture1: WebGLTexture | null = null;
  private framebuffer: WebGLFramebuffer | null = null;

  // Shader programs
  private drawProgram: WebGLProgram | null = null;
  private updateProgram: WebGLProgram | null = null;
  private screenProgram: WebGLProgram | null = null;

  // Buffers
  private quadBuffer: WebGLBuffer | null = null;

  // State
  private currentParticleStateTexture = 0;
  private options: ParticleSystemOptions;
  private animationFrame: number | null = null;

  // Wind texture dimensions
  private windTextureSize = { width: 0, height: 0 };

  constructor(canvas: HTMLCanvasElement, options: Partial<ParticleSystemOptions> = {}) {
    this.canvas = canvas;
    this.options = {
      numParticles: 65536, // 256x256
      particleSpeed: 1.0,
      particleLifetime: 100,
      fadeOpacity: 0.996,
      dropRate: 0.003,
      dropRateBump: 0.01,
      speedFactor: 0.25,
      colors: {
        slow: [0.2, 0.6, 1.0],   // Blue for slow wind
        medium: [0.9, 0.9, 0.2], // Yellow for medium wind
        fast: [1.0, 0.2, 0.2]    // Red for fast wind
      },
      ...options
    };

    const gl = canvas.getContext('webgl', {
      antialiasing: false,
      depth: false,
      stencil: false,
      alpha: true,
      premultipliedAlpha: false,
      preserveDrawingBuffer: false
    }) as WebGLRenderingContext | null;

    if (!gl) {
      throw new Error('WebGL not supported');
    }

    this.gl = gl;
    this.initializeWebGL();
  }

  private initializeWebGL(): void {
    const gl = this.gl;

    // Enable required extensions
    const requiredExtensions = [
      'OES_texture_float',
      'OES_texture_float_linear'
    ];

    requiredExtensions.forEach(ext => {
      if (!gl.getExtension(ext)) {
        console.warn(`WebGL extension ${ext} not available, falling back`);
      }
    });

    // Create shader programs
    this.createShaderPrograms();

    // Create buffers
    this.createBuffers();

    // Initialize particle state textures
    this.initializeParticleTextures();
  }

  private createShaderPrograms(): void {
    const gl = this.gl;

    // Vertex shader for drawing particles
    const drawVertexShader = this.createShader(gl.VERTEX_SHADER, `
      precision mediump float;

      attribute vec2 a_pos;
      uniform vec2 u_resolution;
      uniform sampler2D u_particles;
      uniform vec2 u_particles_res;

      varying vec2 v_particle_pos;

      void main() {
        vec4 color = texture2D(u_particles, a_pos);

        // Decode particle position from RGBA
        vec2 pos = vec2(
          color.r + color.b * 256.0,
          color.g + color.a * 256.0
        );

        v_particle_pos = pos;

        // Convert to screen coordinates
        gl_Position = vec4(
          (pos / u_resolution * 2.0 - 1.0) * vec2(1, -1),
          0,
          1
        );
        gl_PointSize = 1.0;
      }
    `);

    // Fragment shader for drawing particles
    const drawFragmentShader = this.createShader(gl.FRAGMENT_SHADER, `
      precision mediump float;

      uniform sampler2D u_wind;
      uniform vec2 u_wind_res;
      uniform vec2 u_wind_min;
      uniform vec2 u_wind_max;

      varying vec2 v_particle_pos;

      vec3 getWindColor(float speed) {
        vec3 slowColor = vec3(0.2, 0.6, 1.0);   // Blue
        vec3 mediumColor = vec3(0.9, 0.9, 0.2); // Yellow
        vec3 fastColor = vec3(1.0, 0.2, 0.2);   // Red

        float normalizedSpeed = clamp(speed / 30.0, 0.0, 1.0);

        if (normalizedSpeed < 0.5) {
          return mix(slowColor, mediumColor, normalizedSpeed * 2.0);
        } else {
          return mix(mediumColor, fastColor, (normalizedSpeed - 0.5) * 2.0);
        }
      }

      void main() {
        vec2 windPos = (v_particle_pos - u_wind_min) / (u_wind_max - u_wind_min);
        vec2 wind = texture2D(u_wind, windPos).rg;

        float speed = length(wind) * 100.0; // Convert to reasonable speed units
        vec3 color = getWindColor(speed);

        gl_FragColor = vec4(color, 0.8);
      }
    `);

    // Vertex shader for updating particles
    const updateVertexShader = this.createShader(gl.VERTEX_SHADER, `
      precision mediump float;

      attribute vec2 a_pos;
      varying vec2 v_tex_pos;

      void main() {
        v_tex_pos = a_pos;
        gl_Position = vec4(a_pos * 2.0 - 1.0, 0, 1);
      }
    `);

    // Fragment shader for updating particles
    const updateFragmentShader = this.createShader(gl.FRAGMENT_SHADER, `
      precision mediump float;

      uniform sampler2D u_particles;
      uniform sampler2D u_wind;
      uniform vec2 u_wind_res;
      uniform vec2 u_wind_min;
      uniform vec2 u_wind_max;
      uniform float u_speed_factor;
      uniform float u_drop_rate;
      uniform float u_drop_rate_bump;
      uniform vec2 u_resolution;

      varying vec2 v_tex_pos;

      // Pseudo-random number generator
      float rand(vec2 co) {
        return fract(sin(dot(co.xy, vec2(12.9898, 78.233))) * 43758.5453);
      }

      void main() {
        vec4 color = texture2D(u_particles, v_tex_pos);

        // Decode current particle position
        vec2 pos = vec2(
          color.r + color.b * 256.0,
          color.g + color.a * 256.0
        );

        // Get wind at current position
        vec2 windPos = (pos - u_wind_min) / (u_wind_max - u_wind_min);
        vec2 wind = texture2D(u_wind, windPos).rg;

        // Check if we need to drop this particle
        float windSpeed = length(wind);
        float dropRate = u_drop_rate + windSpeed * u_drop_rate_bump;

        bool shouldDrop = rand(pos + v_tex_pos) < dropRate;

        if (shouldDrop || pos.x < u_wind_min.x || pos.x > u_wind_max.x ||
            pos.y < u_wind_min.y || pos.y > u_wind_max.y) {
          // Reset particle to random position
          pos = u_wind_min + (u_wind_max - u_wind_min) * vec2(
            rand(v_tex_pos + pos),
            rand(v_tex_pos.yx + pos.yx)
          );
        } else {
          // Update particle position based on wind
          pos += wind * u_speed_factor;
        }

        // Encode position back to RGBA
        gl_FragColor = vec4(
          fract(pos.x),
          fract(pos.y),
          floor(pos.x) / 256.0,
          floor(pos.y) / 256.0
        );
      }
    `);

    // Screen shader for final rendering
    const screenVertexShader = this.createShader(gl.VERTEX_SHADER, `
      precision mediump float;

      attribute vec2 a_pos;
      varying vec2 v_tex_pos;

      void main() {
        v_tex_pos = a_pos;
        gl_Position = vec4(a_pos * 2.0 - 1.0, 0, 1);
      }
    `);

    const screenFragmentShader = this.createShader(gl.FRAGMENT_SHADER, `
      precision mediump float;

      uniform sampler2D u_screen;
      uniform float u_fade_opacity;

      varying vec2 v_tex_pos;

      void main() {
        vec4 color = texture2D(u_screen, v_tex_pos);
        gl_FragColor = vec4(color.rgb * u_fade_opacity, color.a);
      }
    `);

    // Create programs
    this.drawProgram = this.createProgram(drawVertexShader, drawFragmentShader);
    this.updateProgram = this.createProgram(updateVertexShader, updateFragmentShader);
    this.screenProgram = this.createProgram(screenVertexShader, screenFragmentShader);
  }

  private createShader(type: number, source: string): WebGLShader {
    const gl = this.gl;
    const shader = gl.createShader(type);

    if (!shader) {
      throw new Error('Failed to create shader');
    }

    gl.shaderSource(shader, source);
    gl.compileShader(shader);

    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const error = gl.getShaderInfoLog(shader);
      gl.deleteShader(shader);
      throw new Error(`Shader compilation error: ${error}`);
    }

    return shader;
  }

  private createProgram(vertexShader: WebGLShader, fragmentShader: WebGLShader): WebGLProgram {
    const gl = this.gl;
    const program = gl.createProgram();

    if (!program) {
      throw new Error('Failed to create program');
    }

    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      const error = gl.getProgramInfoLog(program);
      gl.deleteProgram(program);
      throw new Error(`Program linking error: ${error}`);
    }

    return program;
  }

  private createBuffers(): void {
    const gl = this.gl;

    // Create quad buffer for full-screen passes
    const quadVertices = new Float32Array([
      0, 0,
      1, 0,
      0, 1,
      0, 1,
      1, 0,
      1, 1
    ]);

    this.quadBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, quadVertices, gl.STATIC_DRAW);
  }

  private initializeParticleTextures(): void {
    const gl = this.gl;

    const particleTextureSize = Math.sqrt(this.options.numParticles);

    // Create initial particle positions
    const particleData = new Float32Array(this.options.numParticles * 4);

    for (let i = 0; i < this.options.numParticles; i++) {
      const index = i * 4;
      // Random initial positions (will be properly set when wind data loads)
      particleData[index] = Math.random() * 1000;     // X position
      particleData[index + 1] = Math.random() * 1000; // Y position
      particleData[index + 2] = 0;                     // X high bits
      particleData[index + 3] = 0;                     // Y high bits
    }

    // Create textures for double buffering
    this.particleStateTexture0 = this.createTexture(gl.RGBA, particleTextureSize, particleTextureSize, particleData);
    this.particleStateTexture1 = this.createTexture(gl.RGBA, particleTextureSize, particleTextureSize, null);

    // Create framebuffer for off-screen rendering
    this.framebuffer = gl.createFramebuffer();
  }

  private createTexture(format: number, width: number, height: number, data: Float32Array | null): WebGLTexture {
    const gl = this.gl;
    const texture = gl.createTexture();

    if (!texture) {
      throw new Error('Failed to create texture');
    }

    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texImage2D(gl.TEXTURE_2D, 0, format, width, height, 0, format, gl.FLOAT, data);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);

    return texture;
  }

  public updateWeatherData(weatherData: WeatherLayerData): void {
    this.weatherData = weatherData;
    this.createWindTexture();
  }

  private createWindTexture(): void {
    if (!this.weatherData) return;

    const gl = this.gl;
    const { wind } = this.weatherData;
    const { points } = wind;

    const height = points.length;
    const width = points[0]?.length || 0;

    if (width === 0 || height === 0) return;

    this.windTextureSize = { width, height };

    // Create wind texture data (RG = UV wind components)
    const windData = new Float32Array(width * height * 4);

    for (let i = 0; i < height; i++) {
      for (let j = 0; j < width; j++) {
        const point = points[i][j];
        const index = (i * width + j) * 4;

        if (point) {
          windData[index] = point.u;     // U component (R channel)
          windData[index + 1] = point.v; // V component (G channel)
          windData[index + 2] = 0;       // Unused (B channel)
          windData[index + 3] = 1;       // Valid data flag (A channel)
        } else {
          windData[index] = 0;
          windData[index + 1] = 0;
          windData[index + 2] = 0;
          windData[index + 3] = 0;
        }
      }
    }

    // Update or create wind texture
    if (this.windTexture) {
      gl.deleteTexture(this.windTexture);
    }

    this.windTexture = this.createTexture(gl.RGBA, width, height, windData);
  }

  public render(): void {
    if (!this.weatherData || !this.windTexture) return;

    const gl = this.gl;
    gl.disable(gl.DEPTH_TEST);
    gl.disable(gl.STENCIL_TEST);

    // Update particles
    this.updateParticles();

    // Draw particles
    this.drawParticles();

    // Apply fade effect
    this.applyFadeEffect();

    // Swap particle state textures
    this.currentParticleStateTexture = 1 - this.currentParticleStateTexture;
  }

  private updateParticles(): void {
    if (!this.updateProgram || !this.windTexture) return;

    const gl = this.gl;
    const program = this.updateProgram;

    gl.useProgram(program);

    // Set up framebuffer for off-screen rendering
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.framebuffer);

    const targetTexture = this.currentParticleStateTexture === 0 ?
      this.particleStateTexture1 : this.particleStateTexture0;

    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, targetTexture, 0);

    const particleTextureSize = Math.sqrt(this.options.numParticles);
    gl.viewport(0, 0, particleTextureSize, particleTextureSize);

    // Bind current particle state
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.currentParticleStateTexture === 0 ?
      this.particleStateTexture0 : this.particleStateTexture1);
    gl.uniform1i(gl.getUniformLocation(program, 'u_particles'), 0);

    // Bind wind texture
    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, this.windTexture);
    gl.uniform1i(gl.getUniformLocation(program, 'u_wind'), 1);

    // Set uniforms
    const { bounds } = this.weatherData!.wind;
    gl.uniform2f(gl.getUniformLocation(program, 'u_wind_res'),
      this.windTextureSize.width, this.windTextureSize.height);
    gl.uniform2f(gl.getUniformLocation(program, 'u_wind_min'), bounds.west, bounds.south);
    gl.uniform2f(gl.getUniformLocation(program, 'u_wind_max'), bounds.east, bounds.north);
    gl.uniform1f(gl.getUniformLocation(program, 'u_speed_factor'), this.options.speedFactor);
    gl.uniform1f(gl.getUniformLocation(program, 'u_drop_rate'), this.options.dropRate);
    gl.uniform1f(gl.getUniformLocation(program, 'u_drop_rate_bump'), this.options.dropRateBump);
    gl.uniform2f(gl.getUniformLocation(program, 'u_resolution'), this.canvas.width, this.canvas.height);

    // Draw full-screen quad
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuffer);
    const posLocation = gl.getAttribLocation(program, 'a_pos');
    gl.enableVertexAttribArray(posLocation);
    gl.vertexAttribPointer(posLocation, 2, gl.FLOAT, false, 0, 0);

    gl.drawArrays(gl.TRIANGLES, 0, 6);
  }

  private drawParticles(): void {
    if (!this.drawProgram || !this.windTexture) return;

    const gl = this.gl;
    const program = this.drawProgram;

    // Render to screen
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);

    gl.useProgram(program);

    // Enable blending
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

    // Bind updated particle state
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.currentParticleStateTexture === 0 ?
      this.particleStateTexture1 : this.particleStateTexture0);
    gl.uniform1i(gl.getUniformLocation(program, 'u_particles'), 0);

    // Bind wind texture for coloring
    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, this.windTexture);
    gl.uniform1i(gl.getUniformLocation(program, 'u_wind'), 1);

    // Set uniforms
    const { bounds } = this.weatherData!.wind;
    gl.uniform2f(gl.getUniformLocation(program, 'u_resolution'), this.canvas.width, this.canvas.height);
    gl.uniform2f(gl.getUniformLocation(program, 'u_particles_res'),
      Math.sqrt(this.options.numParticles), Math.sqrt(this.options.numParticles));
    gl.uniform2f(gl.getUniformLocation(program, 'u_wind_res'),
      this.windTextureSize.width, this.windTextureSize.height);
    gl.uniform2f(gl.getUniformLocation(program, 'u_wind_min'), bounds.west, bounds.south);
    gl.uniform2f(gl.getUniformLocation(program, 'u_wind_max'), bounds.east, bounds.north);

    // Create particle indices for drawing
    const particleTextureSize = Math.sqrt(this.options.numParticles);
    const particleIndices = new Float32Array(this.options.numParticles * 2);

    for (let i = 0; i < this.options.numParticles; i++) {
      const x = (i % particleTextureSize) / particleTextureSize;
      const y = Math.floor(i / particleTextureSize) / particleTextureSize;
      particleIndices[i * 2] = x;
      particleIndices[i * 2 + 1] = y;
    }

    // Draw particles as points
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, particleIndices, gl.STATIC_DRAW);

    const posLocation = gl.getAttribLocation(program, 'a_pos');
    gl.enableVertexAttribArray(posLocation);
    gl.vertexAttribPointer(posLocation, 2, gl.FLOAT, false, 0, 0);

    gl.drawArrays(gl.POINTS, 0, this.options.numParticles);

    gl.deleteBuffer(buffer);
    gl.disable(gl.BLEND);
  }

  private applyFadeEffect(): void {
    // This would implement a fade effect for particle trails
    // For now, we'll use the built-in fade in the update shader
  }

  public start(): void {
    if (this.animationFrame) return;

    const animate = () => {
      this.render();
      this.animationFrame = requestAnimationFrame(animate);
    };

    animate();
  }

  public stop(): void {
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }
  }

  public resize(width: number, height: number): void {
    this.canvas.width = width;
    this.canvas.height = height;
    this.gl.viewport(0, 0, width, height);
  }

  public dispose(): void {
    this.stop();

    const gl = this.gl;

    // Clean up WebGL resources
    if (this.windTexture) gl.deleteTexture(this.windTexture);
    if (this.particleStateTexture0) gl.deleteTexture(this.particleStateTexture0);
    if (this.particleStateTexture1) gl.deleteTexture(this.particleStateTexture1);
    if (this.framebuffer) gl.deleteFramebuffer(this.framebuffer);
    if (this.quadBuffer) gl.deleteBuffer(this.quadBuffer);
    if (this.drawProgram) gl.deleteProgram(this.drawProgram);
    if (this.updateProgram) gl.deleteProgram(this.updateProgram);
    if (this.screenProgram) gl.deleteProgram(this.screenProgram);
  }
}